import datetime
import io
import unittest
from unittest.mock import *

from doc_scanner import ContractorScanner, AtbScanner


class TestContractorScanner(unittest.TestCase):

    def test_shops_created(self):
        scanner = ContractorScanner()
        contractor = scanner.scan('fixtures/contractor.csv')
        self.assertEquals(len(contractor.shops), 3)

        shop = contractor.get_shop(1003)
        self.assertEquals(shop.num, 1003)
        self.assertEquals(len(shop.invoices), 25)

        self.assertEquals(contractor.get_shop(1008).num, 1008)
        self.assertEquals(contractor.get_shop(105).num, 105)

    def test_invoice_data(self):
        invoice = ContractorScanner.scan_invoice(['01.09.16', '', 'ПСХ00376511', '1037,76'], 1)
        self.assertEquals(invoice.date, datetime.date(2016, 9, 1))
        self.assertEquals(invoice.total, 103776)
        self.assertEquals(invoice.invoice_num, 376511)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_invoice_date_error(self, mock_stdout):
        with self.assertRaises(SystemExit) as cm:
            ContractorScanner.scan_invoice(['01-09-16', '', 'ПСХ00376511', '1037,76'], 1)

        self.assertEquals(
            mock_stdout.getvalue(),
            'Ошибка в документе поставщика строка 1\nНеверный формат даты 01-09-16\n'
        )
        self.assertEqual(cm.exception.code, 1)

    @patch('sys.stdout', new_callable=io.StringIO)
    def test_invoice_total_error(self, mock_stdout):
        with self.assertRaises(SystemExit) as cm:
            ContractorScanner.scan_invoice(['01.09.16', '', 'ПСХ00376511', 'qwer'], 1)
        self.assertEquals(
            mock_stdout.getvalue(),
            'Ошибка в документе поставщика строка 1\nНеверный формат сумы qwer\n'
        )
        self.assertEqual(cm.exception.code, 1)


class TestAtbScanner(unittest.TestCase):

    def test_shops_created(self):
        scanner = AtbScanner()
        atb = scanner.scan('fixtures/atb.csv')
        self.assertEquals(len(atb.shops), 4)

        shop = atb.get_shop(927)
        self.assertEquals(shop.num, 927)
        self.assertEquals(len(shop.invoices), 2)

        self.assertEquals(atb.get_shop(737).num, 737)
        self.assertEquals(atb.get_shop(743).num, 743)
        self.assertEquals(atb.get_shop(1010).num, 1010)

    def test_invoice_data(self):
        invoice = AtbScanner.scan_invoice(
            {
                'date': '01.09.2016',
                'total': '1456,23',
                'invoice_num': '0000222|268S39FI239201'
            },
            1
        )
        self.assertEquals(invoice.date, datetime.date(2016, 9, 1))
        self.assertEquals(invoice.total, 145623)
        self.assertEquals(invoice.invoice_num, 222)

    # @patch('sys.stdout', new_callable=io.StringIO)
    # def test_invoice_date_error(self, mock_stdout):
    #     with self.assertRaises(SystemExit) as cm:
    #         ContractorScanner.scan_invoice(['01-09-16', '', 'ПСХ00376511', '1037,76'], 1)
    #
    #     self.assertEquals(
    #         mock_stdout.getvalue(),
    #         'Ошибка в документе поставщика строка 1\nНеверный формат даты 01-09-16\n'
    #     )
    #     self.assertEqual(cm.exception.code, 1)
    #
    # @patch('sys.stdout', new_callable=io.StringIO)
    # def test_invoice_total_error(self, mock_stdout):
    #     with self.assertRaises(SystemExit) as cm:
    #         ContractorScanner.scan_invoice(['01.09.16', '', 'ПСХ00376511', 'qwer'], 1)
    #     self.assertEquals(
    #         mock_stdout.getvalue(),
    #         'Ошибка в документе поставщика строка 1\nНеверный формат сумы qwer\n'
    #     )
    #     self.assertEqual(cm.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
