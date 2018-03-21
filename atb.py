import csv
import datetime
import re


class Invoice:
    def __init__(self, date: datetime, invoice_type: int, invoice_num: int, total: int, uid: int):
        self.total = total
        self.invoice_num = invoice_num
        self.invoice_type = invoice_type
        self.date = date
        self.id = uid

    def get_formatted_date(self) -> str:
        return self.date.strftime('%d.%m.%Y')

    def get_formatted_total(self) -> str:
        return '{:.2f}'.format(self.total / 100.0).replace('.', ',')

    def __str__(self):
        return 'date: %s, num: %d, total: %d\n' % (self.date, self.invoice_num, self.total)

    def __repr__(self):
        return '\n id: %d date: %s, num: %d, total: %d' % (self.id, self.date, self.invoice_num, self.total)


class Shop:
    def __init__(self, num: int):
        self.num = num
        self.invoices = []

    def add_invoice(self, invoice: Invoice):
        self.invoices.append(invoice)


class Document:
    def __init__(self, name: str):
        self.shops = []
        self.name = name

    def get_shop(self, num: int) -> Shop:
        for shop in self.shops:
            if num == shop.num:
                return shop


def scan_price(text: str):
    """
    Scan price from string, before scanning removes whitespaces
    to avoid issues with floating point values returns price in cents
    """
    text = re.sub('\s', '', text)
    text = text.replace(',', '.')
    return int(round(float(text)*100))


class ScanError(Exception):
    """Base class for exceptions in this module."""
    pass


class ContractorScanner:
    """
    Scanner for csv file of invoices from contractor
    """

    @staticmethod
    def scan(source: str) -> Document:
        csv_file = open(source)
        reader = csv.reader(csv_file)
        shop = Shop(0)
        doc = Document('поставщик')
        for i, row in enumerate(reader):
            if i == 0:
                continue
            if row[1] == '' and row[2] == '':
                shop = Shop(ContractorScanner._scan_shop_number(row[0], i))
                doc.shops.append(shop)
            else:
                shop.add_invoice(ContractorScanner.scan_invoice(row, i))

        return doc

    @staticmethod
    def raise_scan_error(row: int, message: str):
        message = 'Ошибка в документе поставщика строка %d\n%s' % (row, message)
        raise ScanError(message)

    @staticmethod
    def scan_invoice(row: list, row_id: int) -> Invoice:
        """
        Scan invoice data from document row
        """
        # scan date
        try:
            date = datetime.datetime.strptime(row[0], '%d.%m.%y').date()
        except ValueError:
            ContractorScanner.raise_scan_error(row_id, 'Неверный формат даты %s' % row[0])
            return None

        # scan sum
        try:
            total = scan_price(row[3])
        except ValueError:
            ContractorScanner.raise_scan_error(row_id, 'Неверный формат сумы %s' % row[3])
            return None

        # scan invoice number
        number_string = re.sub('[^\d]', '', row[2])
        if number_string != '':
            invoice_num = int(number_string)
        else:
            invoice_num = 0

        return Invoice(date, row[1], invoice_num, total, row_id)

    @staticmethod
    def _scan_shop_number(string: str, row: int) -> int:
        matches = re.findall('№(?:\s+)?\d+', string)
        if len(matches) < 1:
            # todo: log for future check
            ContractorScanner.raise_scan_error(row, 'Не могу получить номер магазина со строки: %s' % string)
        return int(re.sub('[^\d]', '', matches[0]))


class AtbScanner:
    """
    Scanner for csv document of invoices from ATB
    """

    @staticmethod
    def scan(source: str) -> Document:
        csv_file = open(source)
        reader = csv.reader(csv_file)
        doc = Document('АТБ')
        header = []
        for i, row in enumerate(reader):
            if i == 0:
                header = row
                continue
            else:
                sn = row[header.index('[ ]')]
                if sn == '':
                    continue
                shop_number = AtbScanner._scan_shop_number(sn, i)
                shop = doc.get_shop(shop_number)
                if shop is None:
                    shop = Shop(shop_number)
                    doc.shops.append(shop)

                date_col = row[header.index('Внутренняя дата записи')]
                if '' == date_col:
                    date_col = row[header.index('Дата счета-фактуры')]

                number_col = row[header.index('Внутренний порядковый номер')]
                if '' == number_col:
                    number_col = row[header.index('№ счета-фактуры')]

                row_data = {
                    'date': date_col,
                    'total': row[header.index('Сумма по сч.-фактуре')],
                    'invoice_num': number_col
                }
                shop.add_invoice(AtbScanner.scan_invoice(row_data, i))

        return doc

    @staticmethod
    def raise_scan_error(row: int, message: str):
        message = 'Ошибка в документе АТБ строка %d\n%s' % (row, message)
        raise ScanError(message)

    @staticmethod
    def scan_invoice(row_data: dict, row_id: int) -> Invoice:
        """
        Scan invoice data from document row
        """
        # scan date
        try:
            date = datetime.datetime.strptime(row_data['date'], '%d.%m.%Y').date()
        except ValueError:
            AtbScanner.raise_scan_error(row_id, 'Неверный формат даты %s' % row_data['date'])
            return None

        # scan value
        try:
            total = scan_price(row_data['total'])
        except ValueError:
            ContractorScanner.raise_scan_error(row_id, 'Неверный формат сумы %s' % row_data['total'])
            return None

        # scan invoice number
        try:
            invoice_num = int(re.sub('[^\d]', '', row_data['invoice_num'].split('|')[0]))
        except:
            # if invoice number is invalid (in rare cases can be *) then set  1 such number wil be present in diff
            invoice_num = 1

        return Invoice(date, 1, invoice_num, total, row_id)

    @staticmethod
    def _scan_shop_number(string: str, row: int) -> int:
        try:
            string = string[-6:]
            return int(re.sub('[^\d]', '', string))
        except ValueError:
            ContractorScanner.raise_scan_error(row, 'Не могу получить номер магазина со строки: %s' % string)


def get_difference(atb_doc: Document, contractor_doc: Document) -> list:
    """
    Compute differences in invoices between two documents for all shops
    :returns list of grouped invoices in tuples (shop_number, atb_invoice, contractor_invoice, reason)
    """
    difference = []

    for contractor_shop in contractor_doc.shops:
        atb_shop = atb_doc.get_shop(contractor_shop.num)
        if atb_shop is None:
            atb_invoices = []
        else:
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
