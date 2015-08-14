# -*- encoding: utf-8 -*-

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseNotAllowed
from django.contrib.auth import authenticate
from django.contrib.auth import login as djangologin
from django.contrib.auth import logout as djangologout
from django.core.context_processors import csrf
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from django.http import Http404
from django.http import HttpResponseRedirect

from Chat.settings import ANONYMOUS_REDIS_CHANNEL, REGISTERED_REDIS_CHANNEL, logging
from story.decorators import login_required_no_redirect
from story.models import UserProfile, IssueReport, Thread
from story import registration_utils
from story.forms import UserProfileForm, UserProfileReadOnlyForm
from story.registration_utils import check_email, send_email_verification, check_user, check_password
from Chat import settings


logger = logging.getLogger(__name__)


@require_http_methods(['POST'])
def validate_email(request):
	"""
	POST only, validates email during registration
	"""
	email = request.POST.get('email')
	try:
		registration_utils.check_email(email)
		response = settings.VALIDATION_IS_OK
	except ValidationError as e:
		response = e.message
	return HttpResponse(response, content_type='text/plain')


@require_http_methods('POST')
def validate_user(request):
	"""
	Validates user during registration
	"""
	try:
		username = request.POST.get('username')
		registration_utils.check_user(username)
		# hardcoded ok check in register.js
		message = settings.VALIDATION_IS_OK
	except ValidationError as e:
		message = e.message
	return HttpResponse(message, content_type='text/plain')


@require_http_methods('GET')
def home(request):
	"""
	Login or logout navbar is creates by means of create_nav_page
	@return:  the x intercept of the line M{y=m*x+b}.
	"""
	return render_to_response('story/chat.html', csrf(request),  context_instance=RequestContext(request))


@login_required_no_redirect
def logout(request):
	"""
	POST. Logs out into system.
	"""
	djangologout(request)
	response = HttpResponseRedirect('/')
	return response


@require_http_methods(['POST'])
def auth(request):
	"""
	Logs in into system.
	"""
	username = request.POST.get('username')
	password = request.POST.get('password')
	user = authenticate(username=username, password=password)
	if user is not None:
		djangologin(request, user)
		message = settings.VALIDATION_IS_OK
	else:
		message = 'Login or password is wrong'
	response = HttpResponse(message, content_type='text/plain')
	return response


@require_http_methods('GET')
def confirm_email(request):
	"""
	Accept the verification code sent to email
	"""
	code = request.GET.get('code', False)
	try:
		u = UserProfile.objects.get(verify_code=code)
		if u.email_verified is False:
			u.email_verified = True
			u.save()
			message = 'verification code is accepted'
		else:
			message = 'This code is already accepted'
		response = {'message': message}
		return render_to_response('story/confirm_mail.html', response,  context_instance=RequestContext(request))
	except UserProfile.DoesNotExist:
		raise Http404


@require_http_methods('GET')
def get_register_page(request):
	c = csrf(request)
	c.update({'error code': "welcome to register page"})
	return render_to_response("story/register.html", c,  context_instance=RequestContext(request))

@transaction.atomic
@require_http_methods('POST')
def register(request):
	try:
		rp = request.POST
		(username, password, email, verify_email) = (
			rp.get('username'), rp.get('password'), rp.get('email'), rp.get('mailbox'))
		check_user(username)
		check_password(password)
		check_email(email, verify_email == 'Y')
		user = UserProfile(username=username, email=email, sex_str=rp.get('sex'))
		user.set_password(password)
		default_thread, created_default = Thread.objects.get_or_create(name=ANONYMOUS_REDIS_CHANNEL)
		registered_only, created_registered = Thread.objects.get_or_create(name=REGISTERED_REDIS_CHANNEL)
		user.save()
		user.threads.add(default_thread)
		user.threads.add(registered_only)
		user.save()
		logger.info('Signed up new user %s, subscribed for channels %S', user, user.threads)
		# You must call authenticate before you can call login
		auth_user = authenticate(username=username, password=password)
		djangologin(request, auth_user)
		# register,js redirect if message = 'Account created'
		message = settings.VALIDATION_IS_OK
		if verify_email == 'Y':
			send_email_verification(user, request.get_host())
	except ValidationError as e:
		message = e.message
	return HttpResponse(message, content_type='text/plain')


@require_http_methods('GET')
@login_required_no_redirect
def get_profile(request):
	user_profile = UserProfile.objects.get(pk=request.user.id)
	form = UserProfileForm(instance=user_profile)
	c = csrf(request)
	c['form'] = form
	c['date_format'] = settings.DATE_INPUT_FORMATS_JS
	c['readonly'] = False
	return render_to_response('story/change_profile.html', c,  context_instance=RequestContext(request))


@require_http_methods('GET')
def show_profile(request, profile_id):
	try:
		user_profile = UserProfile.objects.get(pk=profile_id)
		form = UserProfileReadOnlyForm(instance=user_profile)
		form.username = user_profile.username
		c = {
			'form': form,
			'readonly': True,
		}
		return render_to_response('story/change_profile.html', c,  context_instance=RequestContext(request))
	except ObjectDoesNotExist:
		raise Http404


@require_http_methods('POST')
@login_required_no_redirect
def save_profile(request):
	user_profile = UserProfile.objects.get(pk=request.user.id)
	form = UserProfileForm(request.POST, request.FILES, instance=user_profile)
	if form.is_valid():
		form.save()
	else:
		return render_to_response('story/response.html', {'message': form.errors}, context_instance=RequestContext(request))
	return HttpResponseRedirect('/')


@require_http_methods(('POST', 'GET'))
def report_issue(request):
	if request.method == 'GET':
		return render_to_response(
			'story/issue.html',  # getattr for anonymous.email
			{'email': getattr(request.user, 'email', '')},
			context_instance=RequestContext(request)
		)
	elif request.method == 'POST':
		issue = IssueReport(
			sender_id=request.user.id,
			browser=request.POST.get('browser'),
			issue=request.POST['issue'],
			email=request.POST.get('email')
		)
		issue.save()
		if request.POST.get('ajax') is True:
			return HttpResponse('ok', content_type='text/plain')
		else:
			return render_to_response(
				'story/response.html',
				{'message': settings.VALIDATION_IS_OK},
				context_instance=RequestContext(request)
			)
	else:
		raise HttpResponseNotAllowed


@require_http_methods('GET')
def hack(request):
	return render_to_response('story/')