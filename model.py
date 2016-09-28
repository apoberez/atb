import datetime


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
