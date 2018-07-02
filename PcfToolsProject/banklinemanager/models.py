import re
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction, IntegrityError
from django.db import models
from django.db.models import Q


class Bank(models.Model):
    ''' Bank is a list of bank (bank account). Linked to one or more BankLine '''
    name = models.CharField('nom', max_length=32, unique=True)
    _account_number = models.SmallIntegerField('numero de compte', unique=True)

    class Meta:
        verbose_name = "Compte Bancaire"

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
                date = bankline_csv[0].strip()
                if len(bankline_csv) >= 6 and re.match(r'^(\d{2})/(\d{2})/(\d{2})$', date) is not None:
                    date_re = re.search(r'^(\d{2})/(\d{2})/(\d{2})$', date)
                    #date_re.reverse()
                    date_formatted = '20%s-%s-%s' % (date_re.group(3), date_re.group(2), date_re.group(1))
                    debit_decimal = bankline_csv[3].replace(",",".") if bankline_csv[3] else Decimal(0)
                    credit_decimal = bankline_csv[4].replace(",",".") if bankline_csv[4] else Decimal(0)

                    bankline = BankLine.objects.create(
                        transaction_date=date_formatted,
                        wording=bankline_csv[2].strip(),
                        transaction_number=bankline_csv[1].strip(),
                        debit=debit_decimal,
                        credit=credit_decimal,
                        bank_detail=bankline_csv[5].strip(),
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

    @classmethod
    def search_bankline(cls, query, type_search, date_start, date_end, sum_min, sum_max, bank_id):
        min_lenght_search = 2
        msg_search = "Recherche"

        if sum_min:
            sum_min = float(sum_min)
        if sum_max:
            sum_max = float(sum_max)

        if query:
            keywords = query.split("\r\n")
            msg_search += ' sur " %s "' % (', '.join(keywords))
            # research contains or startswith keywords
            q_search = Q()
            for keyword in keywords:
                if len(keyword) >= min_lenght_search:
                    if type_search == "startswith":
                        q_search |= Q(wording__istartswith=keyword)
                        q_search |= Q(bank_detail__istartswith=keyword)
                        q_search |= Q(user_comment__istartswith=keyword)
                    else:
                        q_search |= Q(wording__icontains=keyword)
                        q_search |= Q(bank_detail__icontains=keyword)
                        q_search |= Q(user_comment__icontains=keyword)
            bankline_list = BankLine.objects.filter(q_search).select_related('bank')
        elif date_start or sum_min or bank_id:
            bankline_list = BankLine.objects.all().select_related('bank')
            # message += "Vous devez lancer une recherche."
        else:
            bankline_list = None

        if date_start:
            if not date_end:
                date_end = date_start
                msg_search += " en date du %s" % (date_start)
            else:
                msg_search += " entre le %s et le %s" % (date_start, date_end)
            bankline_list = bankline_list.filter(transaction_date__range=(date_start, date_end))

        if sum_min:
            if not sum_max:
                sum_max = sum_min
            if sum_min > sum_max:
                sum_min, sum_max = sum_max, sum_min
            msg_search += " avec un montant entre %s€ et %s€" % (sum_min, sum_max)
            bankline_list = bankline_list.filter(Q(debit__range=(sum_min, sum_max)) | Q(credit__range=(sum_min, sum_max)))

        if bank_id:
            bankline_list = bankline_list.filter(bank=bank_id)
            msg_search += " sur le compte bancaire n°%s" % (bank_id)

        return bankline_list, msg_search
