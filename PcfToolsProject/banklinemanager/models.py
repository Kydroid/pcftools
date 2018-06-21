import re
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction, IntegrityError
from django.db import models


class Bank(models.Model):
    ''' Bank is a list of bank (bank account). Linked to one or more BankLine '''
    name = models.CharField('nom', max_length=32, unique=True)
    _account_number = models.SmallIntegerField('numero de compte', unique=True)

    class Meta:
        verbose_name = "Banque"

    def __str__(self):
        return self.name

    @property
    def get_account_number(self):
	    return self._account_number


class BankLine(models.Model):
    ''' BankLine is a table with list of bank lines (rows). Linked to one Bank '''
    transaction_date = models.DateField('date de transaction')
    wording = models.CharField('libelle', max_length=128)
    transaction_number = models.CharField('numero de transaction', max_length=64, unique=True)
    debit = models.DecimalField('debit', validators=[MaxValueValidator(0)], decimal_places=2,max_digits=8) # ajouter blank=True ?
    credit = models.DecimalField('credit', validators=[MinValueValidator(0)], decimal_places=2,max_digits=8) # ajouter blank=True ?
    bank_detail = models.CharField('détail de la banque', max_length=255, blank=True)
    user_comment = models.CharField('commentaire des utilisateurs', max_length=255, blank=True)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE) # do not allow bank deletion in admin

    class Meta:
        verbose_name = "Ligne Banque"

    def __str__(self):
        return self.wording

    @classmethod
    def insert_data_from_csv(cls, bank, csv_file):
        ''' Try to insert each bank line (row) into database from csv_file. Also need an object Bank.
        Handle data from CEPAC bank. Maybe need a change for data from other bank system. '''
        msg_insert_error = ""
        line_counter = 0

        # parse csv file to import line in database
        for bankline_csv in csv_file:
            try:
                if len(bankline_csv) >= 6 and re.match(r'^(\d{2})/(\d{2})/(\d{2})$', bankline_csv[0]) is not None:
                    date_re = re.search(r'^(\d{2})/(\d{2})/(\d{2})$', bankline_csv[0])
                    #date_re.reverse()
                    date_formatted = '20%s-%s-%s' % (date_re.group(3), date_re.group(2), date_re.group(1))
                    debit_decimal = bankline_csv[3].replace(",",".") if bankline_csv[3] else Decimal(0)
                    credit_decimal = bankline_csv[4].replace(",",".") if bankline_csv[4] else Decimal(0)

                    bankline = BankLine.objects.create(
                        transaction_date=date_formatted,
                        wording=bankline_csv[2],
                        transaction_number=bankline_csv[1],
                        debit=debit_decimal,
                        credit=credit_decimal,
                        bank_detail=bankline_csv[5],
                        bank=bank) # do not allow bank deletion in admin)
                    if bankline is not None:
                        line_counter += 1

            except IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    msg_insert_error += " // Il semble que cette ligne est déjà été importée => %s" % (bankline_csv[1])
                msg_insert_error += " // ERREUR IntegrityError : de transaction data, %s <br/>" % (e)
            except Exception as e:
                msg_insert_error += " // La ligne n'a pas été importée => %s" % (bankline_csv[1])

        return line_counter, msg_insert_error