import csv
import io
from decimal import Decimal

from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import BankLine, Bank

def index(request):
    ''' Show page with all elements of BankLine segmented by page'''
    message = ""
    bankline_list = BankLine.objects.all().order_by('-transaction_date')

    if len(bankline_list) > 0:
        paginator = Paginator(bankline_list, 100)
        page = request.GET.get('page')
        try:
            bankline_list = paginator.page(page)
        except PageNotAnInteger:
            bankline_list = paginator.page(1)
        except EmptyPage:
            bankline_list = paginator.page(paginator.num_pages)
    else:
        message += "Aucune donnée présente."

    context = {
        'bankline_list': bankline_list,
        'paginate': True,
        'message': message
    }
    return render(request, 'banklinemanager/listing.html', context)

def search(request):
    ''' Get the query and filters then show page with result of query'''
    message = ""
    total_credit = 0
    total_debit = 0
    query = request.POST.get('query')
    if not query:
        bankline_list = None
        message += "Vous devez lancer une recherche."
    else:
        bankline_list = BankLine.objects.filter(wording__icontains=query)
        if len(bankline_list) > 0:
            for bankline in bankline_list:
                total_credit += bankline.credit
                total_debit += bankline.debit
        else:
            message += "Aucun résultat trouvé pour %s" % (query)

    context = {
        'bankline_list': bankline_list,
        'message': message,
        'total_credit' : total_credit,
        'total_debit' : total_debit
    }
    return render(request, 'banklinemanager/search.html', context)

def import_data(request):
    ''' View to import data from csv file. this function read csv file and call BankLine.insert_data_from_csv
    to import in database. At the end, show page with csv import result.
    '''
    message = ""
    message_error = ""
    line_counter = 0

    # check method POST and file imported
    if request.method == 'POST' and request.FILES["csv_file"] is not None:

        try:
            file_uploaded = request.FILES['csv_file'].read()
            decoded_file = file_uploaded.decode('latin-1') #utf-8
            io_string = io.StringIO(decoded_file)
            csv_file = csv.reader(io_string, delimiter=';', quotechar='|')

            bank_id = request.POST.get('bank')
            bank = Bank.objects.get(pk=bank_id)

            # Call BankLine.insert_data_from_csv to import each line data
            line_counter, message_error_lines = BankLine.insert_data_from_csv(bank, csv_file)
            message_error += message_error_lines

        except csv.Error as e:
            message_error += " // Le fichier n'a pas été importé  -- ERREUR csv.Error : imports datas, %s" % (e)
            message_error += ' // file %s, line %d: %s' % (request.FILES['csv_file'], csv_file.line_num, e)
        except Exception as e:
            message_error += " // Le fichier n'a pas été importé  -- file %s, line %d: %s" % (request.FILES['csv_file'], csv_file.line_num, e)
        else:
            message += " // imports des données OK"
        finally:
            io_string.close()
            message += " // %s lignes ont été importés." % (line_counter)


    # show page with csv import result
    banks = Bank.objects.all()
    context = {
        'message': message,
        'message_error': message_error,
        'banks': banks
    }
    return render(request, 'banklinemanager/import_data.html', context)