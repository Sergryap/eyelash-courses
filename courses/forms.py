from django import forms
from django.db.models import Q
from phonenumber_field.formfields import PhoneNumberField

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
				'name': "name",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите ваше имя'",
				'placeholder': "Ваше имя"
			}),
		max_length=100, label='Ваше имя')

	phone = PhoneNumberField(
		widget=forms.TextInput(
			attrs={
				'class': "nbm",
				'name': "nbm",
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите ваше телефон'",
				'placeholder': "Ваш телефон"
			}),
		label='Ваш телефон')

	email = forms.EmailField(
		widget=forms.EmailInput(
			attrs={
				'class': "email",
				'name': "email",
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

	courses = [
		{
			'name': instance.name,
			'number': number,
		} for number, instance in enumerate(Course.objects.filter(~Q(name='Фотогалерея')), start=10)
	]
	choices = [('9', 'Выбери курс')]
	for course in courses:
		choices.append(
			(course['number'], course['name'])
		)

	course = forms.CharField(widget=forms.Select(choices=choices))
