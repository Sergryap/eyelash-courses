from django import forms
from django.db.models import Q
from django.utils import timezone
from phonenumber_field.formfields import PhoneNumberField, RegionalPhoneNumberWidget

from courses.models import Course


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
				'placeholder': "Email"
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

	all_courses = Course.objects.filter(
			~Q(name='Фотогалерея'), scheduled_at__gt=timezone.now(), published_in_bot=True
		)
	choices = [('Change', 'Выбери курс')]
	if all_courses:
		courses = [{'name': instance.name} for instance in all_courses]
		for course in courses:
			choices.append(
				(course['name'], course['name'])
			)
	course = forms.CharField(
		widget=forms.Select(choices=choices),
		required=False
	)
