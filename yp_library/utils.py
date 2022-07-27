from yp_library.models import (
    Reader,
    Book,
    LendRecord,
)

from typing import Union
from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from app.utils import check_user_type


def get_readers_by_user(user: User) -> QuerySet:
    """
    根据学号寻找与user关联的reader，要求必须为个人账号且账号必须通过学号关联至少一个reader，否则抛出AssertionError
    :param user: HttpRequest的User
    :type user: User
    :raises AssertionError: 只允许个人账户登录
    :raises AssertionError: user的学号没有关联任何书房账号
    :return: 与user关联的所有reader
    :rtype: QuerySet
    """
    valid, user_type, _ = check_user_type(user)
    if user_type != "Person":  # 只允许个人账户登录
        raise AssertionError('请使用个人账户登录!')
    my_readers = Reader.objects.filter(
        student_id=user.username).values()  # 获取与当前user的学号对应的所有readers
    if len(my_readers) == 0:
        raise AssertionError('您的学号没有关联任何书房账号!')
    return my_readers


def get_my_records(my_id: str, returned: bool = None, status: Union[list, int] = None) -> QuerySet:
    """
    查询给定读者的借书记录

    :param my_id: reader的id
    :type my_id: str
    :param returned: 如非空，则限定是否已归还, defaults to None
    :type returned: bool, optional
    :param status: 如非空，则限定当前状态, defaults to None
    :type status: Union[list, int], optional
    :return: 查询结果，每个记录除LendRecord的部分属性外还包含其对应的Book表的相关属性，见val_list
    :rtype: QuerySet
    """
    all_records_list = LendRecord.objects.filter(reader_id=my_id)
    val_list = ['book_id__id', 'book_id__identity_code',
                'book_id__title', 'book_id__author', 'book_id__publisher', 'lend_time',
                'due_time', 'return_time', 'returned', 'status']

    if returned is not None:
        results = all_records_list.filter(returned=returned)
    else:
        results = all_records_list

    if isinstance(status, list):
        results = results.filter(Q(status__in=status))
    elif isinstance(status, int):
        results = results.filter(status=status)

    return results.values(*val_list)
