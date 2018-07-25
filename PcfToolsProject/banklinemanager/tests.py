import csv
import io

from django.test import TestCase
from django.urls import reverse
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

from .models import BankLine, Bank

# Create your tests here.

class PrepareDataTestCase(TestCase):
    """Class to test Index page"""
    def setUp(self):
        '''Prepare data for test Search Data page. ran before each test. '''
        self.bank_cepac = Bank.objects.create(name="cepac test", _account_number="123456789", _datafile_format=Bank.FORMAT_CSV)
        self.bank_smc = Bank.objects.create(name="smc test", _account_number="987654321", _datafile_format=Bank.FORMAT_OFX_SGML)
        BankLine.objects.create(transaction_date="2018-03-01",
                                wording="test128 credit",
                                transaction_number="15526026",
                                debit=0.0,
                                credit=100.0,
                                bank_detail="detail de la banque",
                                bank=self.bank_cepac)
        BankLine.objects.create(transaction_date="2018-03-04",
                                wording="test debit",
                                transaction_number="541876454",
                                debit=-200.0,
                                credit=0.0,
                                bank_detail="detail de la banque",
                                bank=self.bank_cepac)

        # useful for wiew with login and permissions required
        self.user = User.objects.create_user('usertest', 'user@test.com', 'userpassword')
        permission_list = Permission.objects.get(codename='can_list')
        permission_search = Permission.objects.get(codename='can_search')
        permission_import = Permission.objects.get(codename='can_import')
        self.user.user_permissions.add(permission_list, permission_search, permission_import)
        self.user.save()
        self.client = Client()
        self.client.login(username='usertest', password='userpassword')


class IndexPageTestCase(PrepareDataTestCase):
    """Class to test Index page"""
    def test_index_page(self):
        """Test that index page returns code 200 OK."""
        response = self.client.get(reverse('banklinemanager:index'))
        self.assertEqual(response.status_code, 200)

    def test_index_data_page(self):
        """Test that index page returns code 200 OK."""
        response = self.client.get(reverse('banklinemanager:index'))
        bankline_list = response.context['bankline_list']
        self.assertTrue(len(bankline_list) > 0)
        self.assertContains(response, 'test128 credit')


class ImportDataPageTestCase(PrepareDataTestCase):
    """Class to test Import Data page"""
    def test_import_data_page(self):
        """Test that import data page returns code 200 OK."""
        response = self.client.get(reverse('banklinemanager:import_data'))
        self.assertEqual(response.status_code, 200)

    def test_import_data_form_csv(self):
        """Test import data from csv string IO"""
        self.str_import_test = """31/03/18;3103201820180331-08.55.26.1 -;credit test;302;;mon test credit;
                    31/03/10;3103201820180331-08.55.26.2 -;vir test;504;;mon test vir;
                    31/03/04;3103201820180331-08.55.26.3 -;cb test;856;;mon test cb;
                    """
        io_string = io.StringIO(self.str_import_test)
        csv_file = csv.reader(io_string, delimiter=';', quotechar='|')
        line_counter, inserted_line_counter, msg_insert_error = BankLine.insert_data_from_csv_cepac(self.bank_cepac, csv_file)
        self.assertTrue(line_counter == 3)
        self.assertTrue(inserted_line_counter == 3)
        self.assertTrue(len(msg_insert_error) == 0)

    def test_import_data_form_ofxsgml(self):
        """Test import data from csv string IO"""
        self.str_import_test = """<BANKTRANLIST>
            <DTSTART>20180601000000
            <DTEND>20180630235959
            <STMTTRN>
            <TRNTYPE>DEBIT
            <DTPOSTED>20180629000000
            <DTAVAIL>20180629000000
            <TRNAMT>-4.40
            <FITID>54f54ef5454
            <REFNUM>test refnum
            <NAME>test name
            </STMTTRN>
            <STMTTRN>
            <TRNTYPE>CREDIT
            <DTPOSTED>20180629000000
            <DTAVAIL>20180629000000
            <TRNAMT>4.40
            <FITID>98rgrgr98rgr
            <REFNUM>test refnum2
            <NAME>test name2
            </STMTTRN>"""
        io_string = io.StringIO(self.str_import_test)
        line_counter, inserted_line_counter, msg_insert_error = BankLine.insert_data_from_ofxsgml(self.bank_smc, io_string.getvalue())
        self.assertTrue(line_counter == 2)
        self.assertTrue(inserted_line_counter == 2)
        self.assertTrue(len(msg_insert_error) == 0)


class SearchPageTestCase(PrepareDataTestCase):
    """Class to test Search Data page"""
    def setUp(self):
        '''Prepare data for test Search Data page. ran before each test. '''
        super(SearchPageTestCase, self).setUp()

        self.query = "test"
        self.type_search = "contains"
        self.date_start = "2018-03-01"
        self.date_end = "2018-03-31"
        self.sum_min = 100
        self.sum_max = 5000
        self.bank_id = 1

    def test_search_page(self):
        """Test that search page returns code 200 OK."""
        response = self.client.get(reverse('banklinemanager:search'))
        self.assertEqual(response.status_code, 200)

    def test_search_result_form1(self):
        """test search form with all args"""
        context_request = {
            'query':self.query,
            'type_search':self.type_search,
            'date_start':self.date_start,
            'date_end':self.date_end,
            'sum_min':self.sum_min,
            'sum_max':self.sum_max,
            'bank': self.bank_id
        }
        response = self.client.post(reverse('banklinemanager:search'), context_request)
        bankline_list = response.context['bankline_list']
        self.assertTrue(len(bankline_list) > 0)
        self.assertContains(response, 'test128 credit')

    def test_search_result_form2(self):
        """test search form with all args except query"""
        context_request = {
            'type_search':self.type_search,
            'date_start':self.date_start,
            'date_end':self.date_end,
            'sum_min':self.sum_min,
            'sum_max':self.sum_max,
            'bank': self.bank_id
        }
        response = self.client.post(reverse('banklinemanager:search'), context_request)
        bankline_list = response.context['bankline_list']
        self.assertTrue(len(bankline_list) > 0)
        self.assertContains(response, 'test128 credit')

    def test_search_result_form3(self):
        """test search form with query, date and sum exact"""
        context_request = {
            'query':self.query,
            'type_search':self.type_search,
            'date_start':self.date_start,
            'sum_min':self.sum_min
        }
        response = self.client.post(reverse('banklinemanager:search'), context_request)
        bankline_list = response.context['bankline_list']
        self.assertTrue(len(bankline_list) == 1)
        self.assertContains(response, 'test128 credit')
