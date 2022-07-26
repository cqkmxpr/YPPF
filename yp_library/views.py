from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from boottest.global_messages import wrong, succeed, message_url, transfer_message_context
from yp_library.utils import get_readers_by_user, search_books
from app.utils import get_sidebar_and_navbar, check_user_access


def welcome(request):
    bar_display = get_sidebar_and_navbar(request.user, "元培书房")
    frontend_dict = {
        "bar_display": bar_display,
    }                                

    # 检查用户身份
    # 要求必须为个人账号且账号必须通过学号关联至少一个reader，否则抛出AssertionError
    # 如果图书检索对账号没有要求，可以删掉这部分
    try:
        my_readers = get_readers_by_user(request.user)
    except AssertionError as e:
        return redirect(message_url(wrong(e)))

    if request.method == "POST" and request.POST:  # POST表明发起检索
        # 采用五种查询条件，即"identity_code", "title", "author", "publisher"和"returned"，可视情况修改
        # returned是精确搜索，剩下四个是包含即可（contains）
        # （暂不提供通过id查询，因为id应该没有实际含义，用到的可能性不大）
        # search_books函数要求输入为六个元素的list，分别表示"id", "identity_code", "title", "author", "publisher"和"returned"的query
        # 这里没有id的query，故在首位插入空串
        query_list = [[k, request.POST[k]]
                      for k in ["identity_code", "title", "author", "publisher"]]
        query_list.insert(0, ["id", ""])
        if len(request.POST.getlist("returned")) == 1:  # 如果对returned有要求
            query_list.append(["returned", True])
        else:  # 对returned没有要求
            query_list.append(["returned", ""])
        frontend_dict["search_results_list"] = search_books(dict(query_list))
    
    return render(request, "yp_library/welcome.html", frontend_dict)


@login_required(redirect_field_name="origin")
@check_user_access(redirect_url="/logout/")
def search(request: HttpRequest) -> HttpResponse:
    """
    图书检索页面

    :param request: 进入检索页面/发起检索的请求
    :type request: HttpRequest
    :return: 仍为search页面，显示检索结果
    :rtype: HttpResponse
    """
    bar_display = get_sidebar_and_navbar(request.user, "书籍搜索结果")
    frontend_dict = {
        "bar_display": bar_display,
     }                              
    transfer_message_context(request.GET, frontend_dict,
                             normalize=True)

    # 检查用户身份
    # 要求必须为个人账号且账号必须通过学号关联至少一个reader，否则抛出AssertionError
    # 如果图书检索对账号没有要求，可以删掉这部分
    try:
        my_readers = get_readers_by_user(request.user)
    except AssertionError as e:
        return redirect(message_url(wrong(e)))

    if request.method == "POST" and request.POST:  # POST表明发起检索
        # 采用五种查询条件，即"identity_code", "title", "author", "publisher"和"returned"，可视情况修改
        # returned是精确搜索，剩下四个是包含即可（contains）
        # （暂不提供通过id查询，因为id应该没有实际含义，用到的可能性不大）
        # search_books函数要求输入为六个元素的list，分别表示"id", "identity_code", "title", "author", "publisher"和"returned"的query
        # 这里没有id的query，故在首位插入空串
        query_list = [[k, request.POST[k]]
                      for k in ["identity_code", "title", "author", "publisher"]]
        query_list.insert(0, ["id", ""])
        if len(request.POST.getlist("returned")) == 1:  # 如果对returned有要求
            query_list.append(["returned", True])
        else:  # 对returned没有要求
            query_list.append(["returned", ""])
        frontend_dict["search_results_list"] = search_books(dict(query_list))

    return render(request, "yp_library/search.html", frontend_dict)


def lendInfo(request):
    bar_display = get_sidebar_and_navbar(request.user, "借阅信息")
    frontend_dict = {
        "bar_display": bar_display,
     }                              
    return render(request, "yp_library/lendinfo.html", frontend_dict)
