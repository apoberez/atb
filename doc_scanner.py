import csv
import datetime
import re

from model import Document, Shop, Invoice

# @todo: handle all possible errors while scanning
# @todo: test coverage


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
            total = int(float(re.sub('\s', '', row[3].replace(',', '.'))) * 100)
        except ValueError:
            ContractorScanner.raise_scan_error(row_id, 'Неверный формат сумы %s' % row[3])
            return None

        # scan invoice number
        if row[2] != '':
            invoice_num = int(re.sub('[^\d]', '', row[2]))
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
                shop_number = AtbScanner._scan_shop_number(row[header.index('[ ]')], i)
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
            ContractorScanner.raise_scan_error(row_id, 'Неверный формат даты %s' % row_data['date'])
            return None

        # scan value
        try:
            total = int(float(row_data['total'].replace(',', '.')) * 100)
        except ValueError:
            ContractorScanner.raise_scan_error(row_id, 'Неверный формат сумы %s' % row_data['total'])
            return None

        # scan invoice number
        invoice_num = int(re.sub('[^\d]', '', row_data['invoice_num'].split('|')[0]))

        return Invoice(date, 1, invoice_num, total, row_id)

    @staticmethod
    def _scan_shop_number(string: str, row: int) -> int:
        try:
            string = string[-6:]
            return int(re.sub('[^\d]', '', string))
        except ValueError:
            ContractorScanner.raise_scan_error(row, 'Не могу получить номер магазина со строки: %s' % string)
