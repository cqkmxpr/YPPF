'''
models.py

- 用户模型
- 应用内模型
   - 字段
   - 方法
   - 模型常量
   - 模型性质
- 模型管理器

修改要求
- 模型
    - 如需导出, 在__all__定义
    - 外键和管理器必须进行类型注释`: Class`
    - 与User有一对一关系的实体类型, 需要定义get_type, get_user和get_display_name方法
        - get_type返回UTYPE常量，且可以作为类方法使用
        - 其它建议的方法
            - get_absolute_url: 返回呈现该对象的url，用于后台跳转等，默认是绝对地址
            - get_user_ava: 返回头像的url路径，名称仅暂定，可选支持作为类方法
        - 此外，还应在ClassifiedUser和constants.py中注册
    - 处于平等地位但内部实现不同的模型, 应定义同名接口方法用于导出同类信息
    - 仅供前端使用的方法，在注释中说明
    - 能被评论的模型, 应继承自CommentBase, 并参考其文档字符串要求
    - 性质
        - 模型更改应通过显式数据库操作，性质应是数据库之外的内容（或只读性质）
        - 通过方法或类方法定义，或使用只读的property，建议使用前者，更加直观
        - 若单一对象有确定的定时任务相对应，应添加related_job_ids
    ...
- 模型管理器
    - 不应导出
    - 若与学期有关，必须至少支持select_current的三类筛选
    - 与User有一对一关系的实体管理器, 需要定义get_by_user方法
        - get_by_user通过关联的User获取实例，至少支持update和activate
    ...

@Date 2022-03-11
'''
from django.db import models, transaction
from django_mysql.models import ListCharField
from django.contrib.auth.models import User
from django.db.models import Q, QuerySet
from django.db.models.signals import post_save
from datetime import datetime, timedelta
from general.constants import *
from random import choice


__all__ = [
    # 模型
    'User',
    'YQPointDistribute',
    'Notification',
    'ModifyRecord',
    'PageLog',
    'ModuleLog',
]

# 兼容Django3.0及以下版本
if not hasattr(QuerySet, '__class_getitem__'):
    QuerySet.__class_getitem__ = classmethod(lambda cls, *args, **kwargs: cls)


def current_year() -> int:
    '''不导出的函数，用于实时获取学年设置'''
    return CURRENT_ACADEMIC_YEAR


def image_url(image, enable_abs=False) -> str:
    '''不导出的函数，返回类似/media/path的url相对路径'''
    # ImageField将None和空字符串都视为<ImageFieldFile: None>
    # 即django.db.models.fields.files.ImageFieldFile对象
    # 该类有以下属性：
    # __str__: 返回一个字符串，与数据库表示相匹配，None会被转化为''
    # url: 非空时返回MEDIA_URL + str(self)， 否则抛出ValueError
    # path: 文件的绝对路径，可以是绝对路径但文件必须从属于MEDIA_ROOT，否则报错
    # enable_abs将被废弃
    path = str(image)
    if enable_abs and path.startswith('/'):
        return path
    return MEDIA_URL + path


class ClassifiedUser(models.Model):
    '''
    已分类的抽象用户模型，定义了与User具有一对一关系的模型的通用接口

    子类默认应当设置一对一字段名和展示字段名，或者覆盖模型和管理器的相应方法
    '''
    class Meta:
        abstract = True

    _USER_FIELD: str = NotImplemented
    _DISPLAY_FIELD: str = NotImplemented
    
    def __str__(self):
        return str(self.get_display_name())

    @staticmethod
    def get_type() -> str:
        '''
        获取模型的用户类型表示

        :return: 用户类型
        :rtype: str
        '''
        return ''
    
    def is_type(self, utype: str) -> bool:
        '''
        判断用户类型

        :param utype: 用户类型
        :type utype: str
        :return: 类型是否匹配
        :rtype: bool
        '''
        return self.get_type() == utype

    def get_user(self) -> User:
        '''
        获取对应的用户

        :return: 当前对象关联的User对象
        :rtype: User
        '''
        return getattr(self, self._USER_FIELD)

    def get_display_name(self) -> str:
        '''
        获取展示名称

        :return: 当前对象的名称
        :rtype: str
        '''
        return getattr(self, self._DISPLAY_FIELD)

    def get_absolute_url(self, absolute=False) -> str:
        '''
        获取主页网址

        :param absolute: 是否返回绝对地址, defaults to False
        :type absolute: bool, optional
        :return: 主页的网址
        :rtype: str
        '''
        url = '/'
        if absolute:
            url = LOGIN_URL.rstrip('/') + url
        return url
    
    def get_user_ava(self=None) -> str:
        '''
        获取头像路径

        :return: 头像路径或默认头像
        :rtype: str
        '''
        return image_url('avatar/person_default.jpg')


class ClassifiedUserManager(models.Manager):
    '''
    已分类的用户模型管理器，定义了与User具有一对一关系的模型管理器的通用接口

    支持通过关联用户获取对象，以及筛选满足条件的对象集合
    '''
    def to_queryset(self, *,
                    update=False, activate=False) -> QuerySet[ClassifiedUser]:
        '''
        将管理器转化为筛选过的QuerySet

        :param update: 加锁, defaults to False
        :type update: bool, optional
        :param activate: 只筛选有效对象, defaults to False
        :type activate: bool, optional
        :return: 筛选后的集合
        :rtype: QuerySet[ClassifiedUser]
        '''
        if activate:
            self = self.activated()
        if update:
            self = self.select_for_update()
        return self.all()

    def get_by_user(self, user: User, *,
                    update=False, activate=False) -> ClassifiedUser:
        '''
        通过关联的User获取实例，仅管理ClassifiedUser子类时正确
        
        :param update: 加锁, defaults to False
        :type update: bool, optional
        :param activate: 只选择有效对象, defaults to False
        :type activate: bool, optional
        :raises: ClassifiedUser.DoesNotExist
        :return: 关联的实例
        :rtype: ClassifiedUser
        '''
        select_range = self.to_queryset(update=update, activate=activate)
        return select_range.get(**{self.model._USER_FIELD: user})

    def activated(self) -> QuerySet[ClassifiedUser]:
        '''筛选有效的对象'''
        return self.all()


class YQPointDistribute(models.Model):
    class DistributionType(models.IntegerChoices):
        # 定期发放的类型
        # 每类型各最多有一个status为Yes的实例
        TEMPORARY = (0, "临时发放")
        WEEK = (1, "每周发放一次")
        TWO_WEEK = (2, "每两周发放一次")
        SEMESTER = (26, "每学期发放一次")  # 一年有52周

    # 发放元气值的上限，多于此值则不发放
    per_max_dis_YQP = models.FloatField("自然人发放元气值上限")
    org_max_dis_YQP = models.FloatField("小组发放元气值上限")
    # 个人和小组所能平分的元气值比例
    # 发放时，从学院剩余元气值中，抽取向自然人分发的数量，平分给元气值低于上限的自然人；小组同理
    per_YQP = models.FloatField("自然人获得的元气值", default=0)
    org_YQP = models.FloatField("小组获得的元气值", default=0)

    start_time = models.DateTimeField("开始时间")

    status = models.BooleanField("是否应用", default=False)
    type = models.IntegerField("发放类型", choices=DistributionType.choices)

    class Meta:
        verbose_name = "元气值发放"
        verbose_name_plural = verbose_name


class NotificationManager(models.Manager):
    def activated(self):
        return self.exclude(status=Notification.Status.DELETE)


class Notification(models.Model):
    class Meta:
        verbose_name = "通知消息"
        verbose_name_plural = verbose_name
        ordering = ["id"]

    receiver: User = models.ForeignKey(
        User, related_name="recv_notice", on_delete=models.CASCADE
    )
    sender: User = models.ForeignKey(
        User, related_name="send_notice", on_delete=models.CASCADE
    )

    class Status(models.IntegerChoices):
        DONE = (0, "已处理")
        UNDONE = (1, "待处理")
        DELETE = (2, "已删除")

    class Type(models.IntegerChoices):
        NEEDREAD = (0, "知晓类")  # 只需选择“已读”即可
        NEEDDO = (1, "处理类")  # 需要处理的事务

    class Title(models.TextChoices):
        # 等待逻辑补充，可以自定义
        TRANSFER_INFORM = "元气值入账通知"
        TRANSFER_CONFIRM = "转账确认通知"
        ACTIVITY_INFORM = "活动状态通知"
        VERIFY_INFORM = "审核信息通知"
        POSITION_INFORM = "成员变动通知"
        TRANSFER_FEEDBACK = "转账回执"
        NEW_ORGANIZATION = "新建小组通知"
        YQ_DISTRIBUTION = "元气值发放通知"
        PENDING_INFORM = "事务开始通知"
        FEEDBACK_INFORM = "反馈通知"


    status = models.SmallIntegerField(choices=Status.choices, default=1)
    title = models.CharField("通知标题", blank=True, null=True, max_length=50)
    content = models.TextField("通知内容", blank=True)
    start_time = models.DateTimeField("通知发出时间", auto_now_add=True)
    finish_time = models.DateTimeField("通知处理时间", blank=True, null=True)
    typename = models.SmallIntegerField(choices=Type.choices, default=0)
    URL = models.URLField("相关网址", null=True, blank=True, max_length=1024)
    bulk_identifier = models.CharField("批量信息标识", max_length=64, default="",
                                        db_index=True)
    anonymous_flag = models.BooleanField("是否匿名", default=False)

    objects: NotificationManager = NotificationManager()

    def get_title_display(self):
        return str(self.title)


class ModifyRecord(models.Model):
    # 仅用作记录，之后大概会删除吧，所以条件都设得很宽松
    class Meta:
        verbose_name = "修改记录"
        verbose_name_plural = verbose_name
        ordering = ["-time"]
    user: User = models.ForeignKey(User, on_delete=models.SET_NULL,
                             related_name="modify_records",
                             to_field='username', blank=True, null=True)
    usertype = models.CharField('用户类型', max_length=16, default='', blank=True)
    name = models.CharField('名称', max_length=32, default='', blank=True)
    info = models.TextField('相关信息', default='', blank=True)
    time = models.DateTimeField('修改时间', auto_now_add=True)


class PageLog(models.Model):
    # 统计Page类埋点数据(PV/PD)
    class Meta:
        verbose_name = "Page类埋点记录"
        verbose_name_plural = verbose_name

    class CountType(models.IntegerChoices):
        PV = 0, "Page View"
        PD = 1, "Page Disappear"

    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.IntegerField('事件类型', choices=CountType.choices)

    page = models.URLField('页面url', max_length=256, blank=True)
    time = models.DateTimeField('发生时间', default=datetime.now)
    platform = models.CharField('设备类型', max_length=32, null=True, blank=True)
    explore_name = models.CharField('浏览器类型', max_length=32, null=True, blank=True)
    explore_version = models.CharField('浏览器版本', max_length=32, null=True, blank=True)


class ModuleLog(models.Model):
    # 统计Module类埋点数据(MV/MC)
    class Meta:
        verbose_name = "Module类埋点记录"
        verbose_name_plural = verbose_name

    class CountType(models.IntegerChoices):
        MV = 2, "Module View"
        MC = 3, "Module Click"

    user: User = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.IntegerField('事件类型', choices=CountType.choices)

    page = models.URLField('页面url', max_length=256, blank=True)
    module_name = models.CharField('模块名称', max_length=64, blank=True)
    time = models.DateTimeField('发生时间', default=datetime.now)
    platform = models.CharField('设备类型', max_length=32, null=True, blank=True)
    explore_name = models.CharField('浏览器类型', max_length=32, null=True, blank=True)
    explore_version = models.CharField('浏览器版本', max_length=32, null=True, blank=True)
