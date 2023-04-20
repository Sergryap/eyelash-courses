from django import forms
from phonenumber_field.formfields import PhoneNumberField, RegionalPhoneNumberWidget
from courses.models import Course, Program


class NamePhoneEmailMixin:
	def __init__(self, email_id: str, padding: str = None):
		self.attrs_name = {
			'class': "name",
			'onfocus': "this.placeholder = ''",
			'onblur': "this.placeholder = 'Введите ваше имя'",
			'placeholder': "Ваше имя"
		}
		self.attrs_phone = {
			'class': "nbm",
			'onfocus': "this.placeholder = ''",
			'onblur': "this.placeholder = 'Введите ваше телефон'",
			'placeholder': "Ваш телефон"
		}
		self.attrs_email = {
			'class': "email",
			'onfocus': "this.placeholder = ''",
			'onblur': "this.placeholder = 'Введите Email'",
			'placeholder': "Email",
			'id': f"{email_id}"
		}
		if padding:
			self.attrs_name.update({'style': f"padding: {padding};"})
			self.attrs_phone.update({'style': f"padding: {padding};"})
			self.attrs_email.update({'style': f"padding: {padding};"})

	def get_name_phone_email(self):
		name = forms.CharField(
			widget=forms.TextInput(attrs=self.attrs_name),
			max_length=100,
			label='Ваше имя'
		)
		phone = PhoneNumberField(
			widget=RegionalPhoneNumberWidget(region='RU', attrs=self.attrs_phone),
			label='Ваш телефон'
		)
		email = forms.EmailField(
			widget=forms.EmailInput(attrs=self.attrs_email),
			label='Email',
			required=False
		)
		return name, phone, email


class ContactForm(forms.Form, NamePhoneEmailMixin):
	name, phone, email = NamePhoneEmailMixin(email_id='id_email_top').get_name_phone_email()
	message = forms.CharField(
		widget=forms.Textarea(
			attrs={
				'onfocus': "this.placeholder = ''",
				'onblur': "this.placeholder = 'Введите сообщение'",
				'placeholder': "Сообщение"
			}),
		max_length=500, label='Сообщение', required=False)
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
	# if programs:
	# 	for program in programs:
	# 		choices.append(
	# 			(program.title, program.title)
	# 		)
	course = forms.CharField(
		widget=forms.Select(choices=choices),
		required=False
	)


class CourseForm(forms.Form):
	name, phone, email = NamePhoneEmailMixin(email_id='id_email_course', padding='0px 0px').get_name_phone_email()


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
