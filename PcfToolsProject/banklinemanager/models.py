from django.core.validators import MaxValueValidator, MinValueValidator

from django.db import models

class Bank(models.Model):
    name = models.CharField('nom', max_length=32, unique=True)
    _account_number = models.SmallIntegerField('numero de compte', unique=True)

    class Meta:
        verbose_name = "Banque"

    def __str__(self):
        return self.name


class BankLine(models.Model):
    transaction_date = models.DateField('date de transaction')
    wording = models.CharField('libelle', max_length=128)
    transaction_number = models.CharField('numero de transaction', max_length=64, unique=True)
    debit = models.IntegerField('debit', validators=[MaxValueValidator(0)]) # ajouter blank=True ?
    credit = models.IntegerField('credit', validators=[MinValueValidator(0)]) # ajouter blank=True ?
    bank_detail = models.CharField('détail de la banque', max_length=255, blank=True)
    user_comment = models.CharField('commentaire des utilisateurs', max_length=255, blank=True)
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE) # do not allow bank deletion in admin

    class Meta:
        verbose_name = "Ligne Banque"

    def __str__(self):
        return self.wording