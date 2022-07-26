from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from boottest.global_messages import wrong, succeed, message_url, transfer_message_context
from yp_library.utils import get_readers_by_user, get_my_records
from app.utils import get_sidebar_and_navbar, check_user_access


def welcome(request):
    bar_display = get_sidebar_and_navbar(request.user, "元培书房")
    frontend_dict = {
        "bar_display": bar_display,
    }
    return render(request, "yp_library/welcome.html", frontend_dict)


def search(request):
    bar_display = get_sidebar_and_navbar(request.user, "书籍搜索结果")
    frontend_dict = {
        "bar_display": bar_display,
    }
    return render(request, "yp_library/search.html", frontend_dict)


@login_required(redirect_field_name="origin")
@check_user_access(redirect_url="/logout/")
def lendInfo(request: HttpRequest) -> HttpResponse:
    """
    借阅信息页面

    :param request: 进入借阅信息页面的请求
    :type request: HttpRequest
    :return: lendinfo页面，显示与当前user的学号关联的所有账号的所有借阅记录
    :rtype: HttpResponse
    """
    bar_display = get_sidebar_and_navbar(request.user, "借阅信息")
    frontend_dict = {
        "bar_display": bar_display,
    }
    transfer_message_context(request.GET, frontend_dict,
                             normalize=True)
    # 检查用户身份，
    # 要求必须为个人账号且账号必须通过学号关联至少一个reader，否则抛出AssertionError
    try:
        my_readers = get_readers_by_user(request.user)
    except AssertionError as e:
        return redirect(message_url(wrong(e)))

    frontend_dict['all_records'] = {}
    frontend_dict['student_id'] = request.user.username
    for reader in my_readers:
        # frontend_dict['all_records']先按reader分组，再按是否returned分组
        frontend_dict['all_records'][reader['id']] = {}
        returned_books = get_my_records(
            reader['id'], returned=True)  # 当前reader所有已还记录
        lent_books = get_my_records(
            reader['id'], returned=False)  # 当前reader所有未还记录
        frontend_dict['all_records'][reader['id']
                                     ]['returned_records_list'] = returned_books
        frontend_dict['all_records'][reader['id']
                                     ]['not_returned_records_list'] = lent_books

    return render(request, "yp_library/lendinfo.html", frontend_dict)
