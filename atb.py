import csv
import re

from doc_scanner import ContractorScanner, AtbScanner
from model import Document, Invoice


def get_difference(atb_doc: Document, contractor_doc: Document) -> list:
    """
    Compute differences in invoices between two documents for all shops
    :returns list of grouped invoices in tuples (shop_number, atb_invoice, contractor_invoice, reason)
    """
    difference = []

    for contractor_shop in contractor_doc.shops:
        atb_shop = atb_doc.get_shop(contractor_shop.num)
        atb_invoices = atb_shop.invoices[:]
        contractor_invoices = contractor_shop.invoices[:]

        filter_contractor_invoices(contractor_invoices)
        filter_atb_invoices(atb_invoices)
        filter_equivalent_invoices(atb_invoices, contractor_invoices)
        difference += get_shop_difference(atb_invoices, contractor_invoices, contractor_shop.num)

    return difference


def get_shop_difference(atb_invoices: list, contractor_invoices: list, shop_number: int):
    """
    Compute differences in invoices between two shops
    :returns list of grouped invoices in tuples (shop_number, atb_invoice, contractor_invoice, reason)
    """
    difference = []

    if len(contractor_invoices) > 0 or len(atb_invoices) > 0:
        print(shop_number)
        print(contractor_invoices)
        print(atb_invoices)
        print('==============================================')

    # union by invoice number
    for contractor_invoice in contractor_invoices[:]:
        for atb_invoice in atb_invoices:
            if atb_invoice.invoice_num == contractor_invoice.invoice_num:
                atb_invoices.remove(atb_invoice)
                contractor_invoices.remove(contractor_invoice)
                error = ''
                if atb_invoice.date != contractor_invoice.date:
                    error += 'Неверная дата '
                if atb_invoice.total != contractor_invoice.total:
                    error += 'Расхождение в сумме'
                difference.append((shop_number, contractor_invoice, atb_invoice, error))
                break

    # union by total invoices that don't have pairs by number
    for contractor_invoice in contractor_invoices[:]:
        for atb_invoice in atb_invoices:
            if atb_invoice.total == contractor_invoice.total:
                atb_invoices.remove(atb_invoice)
                contractor_invoices.remove(contractor_invoice)
                error = ''
                if not (contractor_invoice.invoice_num == 0 and contractor_invoice.total < 0)\
                        and atb_invoice.invoice_num != contractor_invoice.invoice_num:
                    error += 'Неверный номер '
                if atb_invoice.date != contractor_invoice.date:
                    error += 'Неверная дата'
                difference.append((shop_number, contractor_invoice, atb_invoice, error))
                break

    for atb_invoice in atb_invoices:
        difference.append((shop_number, None, atb_invoice, 'Нет накладной у поставщика'))
    for contractor_invoice in contractor_invoices:
        difference.append((shop_number, contractor_invoice, None, 'Нет накладной у атб'))

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
    if computed total equals 0 remove such invoices
    """
    for invoice in contractor_invoices[:]:
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
                        if r_invoice.total == 0:
                            contractor_invoices.remove(r_invoice)
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


def filter_atb_invoices(invoices: list):
    """
    When there are invoices with same data and only
    total positive and negative so invoices cancel each other
    such record are called "storno"
    storno should be removed from diff computing process
    If invoice total = 0 such invoice is technical and should be ignored
    """
    for invoice in invoices[:]:
        if invoice.total == 0:
            invoices.remove(invoice)
            continue
        if invoice.total < 0:
            for comp_invoice in invoices[:]:
                if (invoice.invoice_num == comp_invoice.invoice_num or invoice.date == comp_invoice.date) \
                        and (invoice.total + comp_invoice.total) == 0:
                    invoices.remove(invoice)
                    invoices.remove(comp_invoice)
                    break


def save_diff(difference: list, doc_pass: str):
    """
    Save computed difference to file
    """
    file = open(doc_pass, 'w')
    writer = csv.writer(file)
    writer.writerow([
        'Номер магазина',
        'Дата', 'Номер накладной', 'Сума',
        'Дата(атб)', 'Номер накладной(атб)', 'Сума(атб)', 'Примечания'
    ])
    for row in difference:
        csv_row = [row[0]]
        if row[1] is not None:
            csv_row += [row[1].get_formatted_date(), row[1].invoice_num, row[1].get_formatted_total()]
        else:
            csv_row += ['', '', '']
        if row[2] is not None:
            csv_row += [row[2].get_formatted_date(), row[2].invoice_num, row[2].get_formatted_total()]
        else:
            csv_row += ['', '', '']
        csv_row.append(row[3])
        writer.writerow(csv_row)


if __name__ == '__main__':
    # todo: handle possible scanning errors
    # атб
    atb = AtbScanner.scan('documents/atb.csv')
    # поставщик
    contractor = ContractorScanner.scan('documents/postavshik.csv')
    diff = get_difference(atb, contractor)
    save_diff(diff, 'documents/расхождения.csv')

    print('OK')
