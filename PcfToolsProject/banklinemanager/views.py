import csv
import io
from decimal import Decimal

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import BankLine, Bank
from PcfToolsProject.Utils.utils import cleaned_data

@login_required
@permission_required('banklinemanager.can_list')
def index(request):
    ''' Show page with all elements of BankLine segmented by page'''
    list_message = []
    bankline_list = BankLine.objects.all().order_by('-transaction_date').select_related('bank')

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
        list_message.append("Aucune donnée présente.")

    context = {
        'bankline_list': bankline_list,
        'paginate': True,
        'list_message': list_message
    }
    return render(request, 'banklinemanager/listing.html', context)

@login_required
@permission_required('banklinemanager.can_search')
def search(request):
    ''' Get the query and filters then show page with result of query'''
    msg_search = ""
    list_message = []
    total_credit = 0
    total_debit = 0
    bank_id = cleaned_data(request.POST.get('bank'))
    sum_min = cleaned_data(request.POST.get('sum_min'))
    sum_max = cleaned_data(request.POST.get('sum_max'))
    date_start = cleaned_data(request.POST.get('date_start'))
    date_end = cleaned_data(request.POST.get('date_end'))
    type_search = cleaned_data(request.POST.get('type_search'))
    query = cleaned_data(request.POST.get('query'))

    bankline_list, msg_search = BankLine.search_bankline(query, type_search, date_start, date_end, sum_min, sum_max, bank_id)

    if bankline_list and len(bankline_list) > 0:
        list_message.append(msg_search)
        list_message.append("%s résultat trouvé(s)" % (len(bankline_list)))
        for bankline in bankline_list:
            total_credit += bankline.credit
            total_debit += bankline.debit
    elif query or date_start or sum_min or bank_id:
        list_message.append(msg_search)
        list_message.append("Aucun résultat trouvé pour %s" % (query))

    banks = Bank.objects.all()
    context = {
        'bankline_list': bankline_list,
        'list_message': list_message,
        'total_credit' : total_credit,
        'total_debit' : total_debit,
        'banks': banks
    }
    return render(request, 'banklinemanager/search.html', context)

@login_required
@permission_required('banklinemanager.can_import')
def import_data(request):
    ''' View to import data from csv file. this function read csv file and call BankLine.insert_data_from_csv
    to import in database. At the end, show page with csv import result.
    '''
    list_message = []
    list_message_error = []
    line_counter = 0
    inserted_line_counter = 0

    # check method POST and file imported
    if request.method == 'POST' and request.FILES["csv_file"] is not None:

        try:
            bank_id = request.POST.get('bank')
            bank = Bank.objects.get(pk=bank_id)

            file_uploaded = request.FILES['csv_file'].read()
            decoded_file = file_uploaded.decode('latin-1') #utf-8
            io_string = io.StringIO(decoded_file)

            #if bank.name.lower().startswith("csv cepac"):
            if bank.get_datafile_format == Bank.FORMAT_OFX_SGML:
                # Call BankLine.insert_data_from_ofx to import each line data
                line_counter, inserted_line_counter, message_error_lines = BankLine.insert_data_from_ofxsgml(bank, io_string.getvalue())
                list_message_error.extend(message_error_lines)
            elif bank.get_datafile_format == Bank.FORMAT_CSV:
                csv_file = csv.reader(io_string, delimiter=';', quotechar='|')
                # Call BankLine.insert_data_from_csv to import each line data
                line_counter, inserted_line_counter, message_error_lines = BankLine.insert_data_from_csv_cepac(bank, csv_file)
                list_message_error.extend(message_error_lines)
            elif bank.get_datafile_format == Bank.FORMAT_OFX_XML:
                # (not yet defined) maybe in future version 
                list_message_error.append("Ce compte bancaire est prévu pour importer un fichier %s. \
                    Ce type de fichier n est pas encore géré par cette application." % (Bank.FORMAT_OFX_XML))

        except csv.Error as e:
            list_message_error.append("-> Le fichier n'a pas été importé  -- ERREUR csv.Error lors de l import datas")
            list_message_error.append("--> ERREUR csv.Error = file %s, line %d: %s" % (request.FILES['csv_file'], csv_file.line_num, e))
        except Exception as e:
            list_message_error.append("-> Le fichier n'a pas été importé  -- file %s, %s" % (request.FILES['csv_file'], e))
        else:
            io_string.close()
            list_message.append("-> imports des données OK")
        finally:
            list_message.append("-> %s lignes sur %s ont été importés." % (inserted_line_counter, line_counter))


    # show page with csv import result
    banks = Bank.objects.all()
    context = {
        'list_message': list_message,
        'list_message_error': list_message_error,
        'banks': banks
    }
    return render(request, 'banklinemanager/import_data.html', context)
