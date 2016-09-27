import csv
import re

from doc_scanner import ContractorScanner, AtbScanner
from model import Document, Invoice


def get_difference(atb_doc: Document, contractor_doc: Document) -> list:
    """
    Compute differences in invoices between two documents
    """
    difference = []

    # collect diff by all shops
    for contractor_shop in contractor_doc.shops:
        atb_shop = atb_doc.get_shop(contractor_shop.num)
        atb_invoices = atb_shop.invoices[:]
        contractor_invoices = contractor_shop.invoices[:]

        filter_contractor_invoices(contractor_invoices)
        filter_storno(atb_invoices)
        filter_equivalent_invoices(atb_invoices, contractor_invoices)
        difference += get_shop_difference(atb_invoices, contractor_invoices, contractor_shop.num)

    return difference


def get_shop_difference(atb_invoices: list, contractor_invoices: list, shop_number: int):
    difference = []

    print(shop_number)
    print(contractor_invoices)
    print(atb_invoices)
    print('==============================================')

    for c_invoice in contractor_invoices:
        matched = None
        error = 'Нет накладной у атб'
        for invoice in atb_invoices:
            if invoice.total == c_invoice.total:
                matched = invoice
                atb_invoices.remove(invoice)
                error = ''
                if c_invoice.invoice_num != 0 and invoice.invoice_num != c_invoice.invoice_num:
                    error += 'Неверный номер '
                if invoice.date != c_invoice.date:
                    error += 'Неверная дата'
                break

        if len(atb_invoices) > 0 and matched is None:
            for invoice in atb_invoices:
                if invoice.date == c_invoice.date:
                    matched = invoice
                    atb_invoices.remove(invoice)
                    error = ''
                    if invoice.invoice_num != c_invoice.invoice_num:
                        error += 'Неверный номер '
                    if invoice.total != c_invoice.total:
                        error += 'Расхождение в сумме'
                    break

        if len(atb_invoices) > 0 and matched is None:
            for invoice in atb_invoices:
                if invoice.invoice_num != c_invoice.invoice_num:
                    matched = invoice
                    atb_invoices.remove(invoice)
                    error = ''
                    if invoice.date == c_invoice.date:
                        error += 'Неверная дата '
                    if invoice.total != c_invoice.total:
                        error += 'Расхождение в сумме'
                    break

        difference.append((shop_number, c_invoice, matched, error))

    for invoice in atb_invoices:
        difference.append((shop_number, None, invoice, 'Нет накладной у поставщика'))

    return difference


def filter_equivalent_invoices(atb_invoices: list, contractor_invoices: list):
    """
    Remove same invoices from both collections if data is equivalent
    """
    copy = contractor_invoices[:]
    a_copy = atb_invoices[:]
    for invoice in copy:
        for comp_invoice in a_copy:
            if is_same_invoice(invoice, comp_invoice) \
                    and invoice in contractor_invoices \
                    and comp_invoice in atb_invoices:
                    # todo: check and remove if possible checking
                contractor_invoices.remove(invoice)
                atb_invoices.remove(comp_invoice)
                break


def filter_contractor_invoices(contractor_invoices: list):
    """
    In contractor document invoice can have child invoice
    we should union such invoices before computing difference
    """
    copy = contractor_invoices[:]
    for invoice in copy:
        if invoice.total < 0:
            # todo: move to scanner type scanning logic
            r_invoice_num_match = re.search('\d+', invoice.invoice_type)
            if r_invoice_num_match is not None:
                r_invoice_num = int(r_invoice_num_match.group())
                for r_invoice in contractor_invoices:
                    if r_invoice.invoice_num == r_invoice_num:
                        contractor_invoices.remove(invoice)
                        # todo: maybe add compound total field in Invoice and move this logic to scanner
                        r_invoice.total += invoice.total
                        break


def is_same_invoice(contractor_invoice: Invoice, atb_invoice: Invoice) -> bool:
    """
    Compare invoices between two documents
    for now it's possible that contractor invoices with return type
    can be without "invoice number" so temporary we should ignore it in this case
    """
    return (contractor_invoice.invoice_num == atb_invoice.invoice_num
            or (contractor_invoice.total < 0 and contractor_invoice.invoice_num == 0)) \
           and contractor_invoice.date == atb_invoice.date \
           and contractor_invoice.total == atb_invoice.total


def filter_storno(atb_invoices: list):
    """
    When there are invoices with same data and only
    total positive and negative so invoices cancel each other
    such record are called "storno"
    storno should be removed from diff computing process
    """
    atb_invoices_copy = atb_invoices[:]
    for invoice in atb_invoices_copy:
        for comp_invoice in atb_invoices_copy:
            if (invoice.invoice_num == comp_invoice.invoice_num or invoice.date == comp_invoice.date) \
                    and invoice.total < 0 \
                    and (invoice.total + comp_invoice.total) == 0:
                atb_invoices.remove(invoice)
                atb_invoices.remove(comp_invoice)
                break


def save_diff(difference):
    """
    Save computed difference to file
    """
    file = open('documents/diff.csv', 'w')
    writer = csv.writer(file)
    writer.writerow([
        'Номер магазина',
        'Дата', 'Номер накладной', 'Сума',
        'Дата(атб)', 'Номер накладной(атб)', 'Сума(атб)', 'Примечания'
    ])
    for row in difference:
        csv_row = [row[0]]
        if row[1] is not None:
            csv_row += [row[1].date, row[1].invoice_num, row[1].total / 100]
        else:
            csv_row += ['', '', '']
        if row[2] is not None:
            csv_row += [row[2].date, row[2].invoice_num, row[2].total / 100]
        else:
            csv_row += ['', '', '']
        csv_row.append(row[3])
        writer.writerow(csv_row)


if __name__ == '__main__':
    # todo: handle possible scanning errors
    atb = AtbScanner.scan('documents/atb.csv')
    contractor = ContractorScanner.scan('documents/contractor.csv')
    diff = get_difference(atb, contractor)
    save_diff(diff)

    print('OK')
