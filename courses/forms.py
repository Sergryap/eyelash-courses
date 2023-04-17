from django import forms
from django.db.models import Q
from django.utils import timezone
from phonenumber_field.formfields import PhoneNumberField, RegionalPhoneNumberWidget

from courses.models import Course, Program


class ContactForm(forms.Form):

	message = forms.CharField(
		widget=forms.Textarea(
			attrs={
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите сообщение'",
				'placeholder': "Сообщение"
			}),
		max_length=500, label='Сообщение', required=False)

	name = forms.CharField(
		widget=forms.TextInput(
			attrs={
				'class': "name",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите ваше имя'",
				'placeholder': "Ваше имя"
			}),
		max_length=100, label='Ваше имя')

	phone = PhoneNumberField(
		widget=RegionalPhoneNumberWidget(
			region='RU',
			attrs={
				'class': "nbm",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите ваше телефон'",
				'placeholder': "Ваш телефон"
			}),
		label='Ваш телефон')

	email = forms.EmailField(
		widget=forms.EmailInput(
			attrs={
				'class': "email",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите Email'",
				'placeholder': "Email",
				'id': "id_email_top"
			}),
		label='Email', required=False)

	date = forms.CharField(
		widget=forms.TextInput(
			attrs={
				'id': "datepicker",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите желаемую дату'",
				'placeholder': "Желаемая дата"
			}),
		label='Желаемая дата', required=False)

	programs = Program.objects.all()
	choices = [('Change', 'Выбери курс')]
	if programs:
		for program in programs:
			choices.append(
				(program.title, program.title)
			)
	course = forms.CharField(
		widget=forms.Select(choices=choices),
		required=False
	)


class CourseForm(forms.Form):

	name = forms.CharField(
		widget=forms.TextInput(
			attrs={
				'class': "name",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите ваше имя'",
				'placeholder': "Ваше имя",
				'style': "padding: 0px 0px;"
			}),
		max_length=100, label='Ваше имя')

	phone = PhoneNumberField(
		widget=RegionalPhoneNumberWidget(
			region='RU',
			attrs={
				'class': "nbm",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите ваше телефон'",
				'placeholder': "Ваш телефон",
				'style': "padding: 0px 0px;"
			}),
		label='Ваш телефон')

	email = forms.EmailField(
		widget=forms.EmailInput(
			attrs={
				'class': "email",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите Email'",
				'placeholder': "Email",
				'id': "id_email_course",
				'style': "padding: 0px 0px;"
			}),
		label='Email', required=False)


class SubscribeForm(forms.Form):
	email = forms.EmailField(
		widget=forms.EmailInput(
			attrs={
				'class': "course",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите Email'",
				'placeholder': "Email",
				'id': "id_email_footer",
				'style': "padding: 0px 0px;"
			})
	)
