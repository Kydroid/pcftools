import re
from decimal import Decimal
import logging as lg

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import transaction, IntegrityError
from django.db import models
from django.db.models import Q


class Bank(models.Model):
    ''' Bank is a list of bank (bank account). Linked to one or more BankLine '''
    FORMAT_CSV = "CSV"
    FORMAT_OFX_SGML = "OFX1"
    FORMAT_OFX_XML = "OFX2"
    FORMAT_DATAFILE_ACCEPTED = (
        (FORMAT_CSV, "Datafile format CSV for CEPAC only"),
        (FORMAT_OFX_SGML, "Datafile format OFX SGML"),
        (FORMAT_OFX_XML, "Datafile format OFX XML"),
        )

    name = models.CharField('nom', max_length=32, unique=True)
    _account_number = models.BigIntegerField('numero de compte', unique=True)
    _datafile_format = models.CharField(max_length=4, choices=FORMAT_DATAFILE_ACCEPTED, default=FORMAT_OFX_SGML)

    class Meta:
        verbose_name = "Compte Bancaire"

    def __str__(self):
        return self.name

    @property
    def get_account_number(self):
        return self._account_number

    @property
    def get_datafile_format(self):
        return self._datafile_format


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
        permissions = (
            ("can_list", "Can list and see all banklines"),
            ("can_search", "Can search banklines"),
            ("can_import", "Can import data bankline from datafile"),
        )

    def __str__(self):
        return self.wording


    @classmethod
    def insert_data_from_ofxsgml(cls, bank, ofx_file):
        ''' Try to insert each bank line (row) into database from ofx_file. Also need an object Bank.
        Handle data from bank with ofx file format. Maybe need a change for data from other bank system. '''
        msg_insert_error = []
        line_counter = 0
        inserted_line_counter = 0

        #ofx_file = ofx_file.replace('\r','').replace('\n','')
        transactions = re.findall(r'<STMTTRN>.*?</STMTTRN>', ofx_file, re.DOTALL)
        for transaction in transactions:
            try:
                date_re = re.search(r'<DTPOSTED>(\d{4})(\d{2})(\d{2})(.*?)\n', transaction)
                if date_re is not None:
                    date_formatted = '%s-%s-%s' % (date_re.group(1), date_re.group(2), date_re.group(3))
                else:
                    raise Exception("Erreur : La date de la transaction n a pas pu etre recuperee.")
                type_debit_credit = re.search(r'<TRNTYPE>(.*?)\n', transaction).group(1)
                #montant = re.search(r'<TRNAMT>(.*?)\n', transaction).group(1)
                montant = re.search(r'<TRNAMT>([+-]?\d+[,\.]?\d*).*\n', transaction).group(1)
                montant = montant.replace(",",".")
                debit = montant if type_debit_credit.lower().startswith("debit") else Decimal(0)
                credit = montant if type_debit_credit.lower().startswith("credit") else Decimal(0)
                fitid = re.search(r'<FITID>(.*?)\n', transaction).group(1)
                name = re.search(r'<NAME>(.*?)\n', transaction).group(1)
                memo = re.search(r'<MEMO>(.*?)\n', transaction)
                memo = memo.group(1) if memo else ""

                line_counter += 1
                bankline = BankLine.objects.create(
                    transaction_date=date_formatted,
                    wording=name.strip(),
                    transaction_number=fitid.strip(),
                    debit=debit,
                    credit=credit,
                    bank_detail=memo.strip(),
                    bank=bank)
                if bankline is not None:
                    inserted_line_counter += 1

            except IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    msg_insert_error.append("-> Il semble que cette ligne est déjà été importée = %s" % (fitid))
                lg.warning("=> ERREUR IntegrityError : de transaction data, %s" % (e))
            except Exception as e:
                msg_insert_error.append("-> La ligne suivante n'a pas été importée => %s" % (transaction[:64]))
                lg.warning(e)

        return line_counter, inserted_line_counter, msg_insert_error

    @classmethod
    def insert_data_from_csv_cepac(cls, bank, csv_file):
        ''' (No recommended) Try to insert each bank line (row) into database from csv_file. Also need an object Bank.
        Handle data from CEPAC bank (tested only with Cepac). Maybe need a change for data from other bank system. '''
        msg_insert_error = []
        line_counter = 0
        inserted_line_counter = 0

        # parse csv file to import line in database
        for bankline_csv in csv_file:
            try:
                if len(bankline_csv) >= 6:
                    date = bankline_csv[0].strip()
                    if re.match(r'^(\d{2})/(\d{2})/(\d{2})$', date) is not None:
                        date_re = re.search(r'^(\d{2})/(\d{2})/(\d{2})$', date)
                        date_formatted = '20%s-%s-%s' % (date_re.group(3), date_re.group(2), date_re.group(1))
                        debit_decimal = bankline_csv[3].replace(",",".") if bankline_csv[3] else Decimal(0)
                        credit_decimal = bankline_csv[4].replace(",",".") if bankline_csv[4] else Decimal(0)
                        # Delete multiple whitespace in wording and detail to avoid future search errors.
                        bank_detail = re.sub(' +', ' ', bankline_csv[5]).strip()
                        wording = re.sub(' +', ' ', bankline_csv[2]).strip()
                        if re.match(r'^(.*) -$', bankline_csv[1]) is not None:
                            # Get transaction number (fitid) without " -" to match with ofx datafile by CEPAC
                            transaction_number = re.search(r'^(.*) -$', bankline_csv[1]).group(1)
                        else:
                            transaction_number = bankline_csv[1].strip()

                        line_counter += 1
                        bankline = BankLine.objects.create(
                            transaction_date=date_formatted,
                            wording=wording,
                            transaction_number=transaction_number,
                            debit=debit_decimal,
                            credit=credit_decimal,
                            bank_detail=bank_detail,
                            bank=bank)
                        if bankline is not None:
                            inserted_line_counter += 1

            except IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    msg_insert_error.append("-> Il semble que cette ligne est déjà été importée = %s" % (transaction_number))
                lg.warning("=> ERREUR IntegrityError : de transaction data, %s" % (e))
            except Exception as e:
                msg_insert_error.append("-> La ligne suivante n'a pas été importée => %s" % (transaction_number))
                lg.warning(e)

        return line_counter, inserted_line_counter, msg_insert_error

    @classmethod
    def search_bankline(cls, query, type_search, date_start, date_end, sum_min, sum_max, bank_id):
        """ Create a query to select a banklines list filtered with one or more filters."""
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
