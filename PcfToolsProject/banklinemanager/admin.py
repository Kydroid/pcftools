from django.contrib import admin

from .models import Bank, BankLine

""" Class BankeAdmin """
@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    search_fields = ['name']

""" Class BankLineAdmin """
@admin.register(BankLine)
class BankLineAdmin(admin.ModelAdmin):
	list_display = ["transaction_date", "wording", "transaction_number", "debit", "credit", "bank_detail", "bank", "user_comment"]
	list_filter = ['transaction_date']
	search_fields = ['wording', 'bank_detail', 'user_comment']
	readonly_fields = ["transaction_date", "wording", "transaction_number", "debit", "credit", "bank_detail", "bank"]
	#fields = ["user_comment"]

	def has_add_permission(self, request):
		return False

        