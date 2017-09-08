spicy.history
=============

Приложение Django для SpicyCMS. Использует [концепцию реиспользования кода и конфигурации spicy.core](https://github.com/spicycms/spicy.core). Это простое приложение использует по умолчанию типовые шаблоны и часть логики ``spicy.core.admin``, предоставляет сервис ``HistoryService``, реализующий действия с историей изменений - сохранение, просмотр, откат к предыдущим версиям.

Для запуска необходима версия 1.4.11 - 1.5.12 Django.

Назначение
----------
Модуль предназначен для ведения истории изменений объектов на сайте, просмотра изменений в стиле ``git diff``, отката к предыдущим версиям. Вы можете настроить spicy.history так, чтобы отслеживать изменения документов, медиафайлов, профилей пользователей, любых других объектов, любых полей этих объектов. 

Подключить spicy.history к вашему приложению
--------------------------------------------
Установите модуль с помощью pip: ``pip install git+https://github.com/spicycms/spicy.history#egg=spicy.history``.

Добавьте в настройки установленных приложений и в список сервисов в ``settings.py``:
```
INSTALLED_APPS = (
    ...
    'spicy.history',
    ...
)

SERVICES = (
    'spicy.history.services.HistoryService',
    ...
)
```

Добавьте в ``urls.py`` путь для модуля spicy.history в ``settings.py``:
```
urlpatterns = patterns('',
    ...
    url(r'^', include('spicy.history.urls', namespace='history')),
    ...
)
```

После этого необходимо выполнить ``manage.py syncdb``, чтобы Django создала таблицы spicy.history в базе данных. Ваше приложение настроено, чтобы использовать spicy.history. Теперь нужно [настроить](./README.md#Настройка-истории-для-объектов), для каких объектов на сайте вести историю.

Настройка истории для объектов
------------------------------
Вы можете указать spicy.history отслеживать любое поле любой модели приложения. Для этого в ``settings.py`` укажите:
```
OBSERVED_FIELDS = {
    'webapp.Document': ('body', 'slug', 'title', 'pub_date'),
    ...
}
```
В этом примере, spicy.history настроен на отслеживание модели документа ``Document``, будут сохраняться изменения для полей ``body``, ``slug``, ``title``, ``pub_date``. Аналогично вы можете добавить и другие модели в ``OBSERVED_FIELDS``, перечислив их поля.

Другие настройки spicy.history
------------------------------
* ``AUTHORS_TOP_LIMIT`` - максимальное количество наиболее часто изменяющих объекты пользователей. Выводится в список активных пользователей в шаблоне ``history/authors_top.html``, значение по умолчанию - 10.

Для Django программиста
-----------------------
Ниже приведены детали реализации spicy.history с описанием моделей и методов сервиса.

### Модели spicy.history
Модуль использует 2 основные модели - ``Action`` и ``Diff``. ``Action`` хранит информацию о том, кем, когда и какой [тип изменения](https://github.com/spicycms/spicy.history/blob/develop/src/spicy/history/defaults.py#L12) был сделан для определенного объекта. Модель ``Diff`` хранит данные о том, какое поле было изменено, новое значение и версию.

Эти модели имеют методы и свойства:

* ``Diff.first_version()`` - возвращает первую версию отслеживаемого поля объекта. Реализовано с декоратором ``@cached_property``.

Сразу после подключения spicy.history при создании объекта отслеживаемой модели происходит первая запись в историю - о создании объекта, это считается первой версией. Любое действие на запись в базу данных через ORM будет добавлять записи в историю изменений.

Если вы подключаете spicy.history к уже работающему приложению, например, для отслеживания документов, то первые версии не будут созданы автоматически, вам нужно будет создать их "вручную" (используя Django ORM), например, через команду менеджмента.

* ``Diff.prev_version()`` - возвращает предыдущую версию для текущего объекта класса ``Diff``. Реализовано с декоратором ``@cached_property``.

* ``Diff.next_version()`` - возвращает следующую версию для текущего объекта класса ``Diff``. Реализовано с декоратором ``@cached_property``.

Если у объекта нет предыдущей или следующей версии, методы ``prev_version`` и ``prev_version`` возвращают ``None``.

* ``Diff.last_version()`` - возвращает последнюю версию отслеживаемого поля объекта. Реализовано с декоратором ``@cached_property``.

* ``Diff.get_version_text()`` - возвращает текстовое представление изменения, с версией.

* ``Diff.verbose_field_name()`` - возвращает varbose_name поля, для которого было сделано это изменение.


### Сервис spicy.history
Кроме моделей, spicy.history также предоставляет сервис ``HistoryService``, который дает доступ к провайдеру с [полезными методами](./README.md#Методы-провайдера-spicyhistory) для истории изменений, которые вы можете использовать в ваших обработчиках:

```
from spicy.core.service import api

def your_view(request):
    item = YourModel.objects.all()[0]   # случайный объект, для которого настроено отслеживание изменений
    hist_service = api.register['history']                      # сервис spicy.history
    prov = hist_service.get_provider_instances(consumer=item)   # провайдер spicy.history
    # тут вы можете использовать методы провайдера
```

#### Методы провайдера spicy.history
Кроме использования провайдера в ваших обработчиках через ``api.register['history']``, вы можете обращаться к ним напрямую по URL.

* ``HistoryProvider.list(request, consumer_type, consumer_id)`` - список изменений указанного объекта.<br>
Доступ к методу вы можете получить из шаблона, используя ``{% url 'service:public:history-list' 'document' doc.pk as history_url %}`` - так в контекст шаблона будет добавлена переменная ``history_url`` - путь к методу (в этом примере тип объекта ``Document``, с ``pk=doc.pk``). Метод возвращает шаблон services/list.html, в его контексте доступны переменные ``nav``, ``objects_list``, ``paginator``, ``consumer``, ``consumer_type_id``, ``fields``. Описание переменных смотрите [ниже](./README.md#Список-переменных-шаблонов-spicyhistory).

* ``HistoryProvider.list_by_field(request, consumer_type, consumer_id, field)`` - список изменений указанного объекта по заданному полю.<br>
Доступ к методу вы можете получить из шаблона, используя ``{% url 'service:public:history-list_by_field' 'document' doc.pk 'is_public' as history_url %}``, переменная контекста history_url будет содержать URL для обращения к нему. В этом примере будет сгенерирован URL для получения списка изменений поля ``is_public`` объекта типа ``Document`` с id, равным ``doc.pk``. Метод возвращает шаблон services/list.html, в нем доступны переменные ``prov`` и ``consumer``, описание [ниже](./README.md#Список-переменных-шаблонов-spicyhistory).

* ``HistoryProvider.rollback(request, diff_id)`` - откат изменений к указанной версии (объекту ``Diff``).<br>
Получить URL из шаблона можно с помощью ``{% url 'service:public:history-rollback' diff.pk as rollback_url %}``. Этот метод возвращает AJAX ответ, содержащий поля ``status``, ``message`` и ``next_url``, описание переменных [ниже](./README.md#Список-переменных-шаблонов-spicyhistory).

* ``HistoryProvider.authors_top(request)`` - выводить список наиболее часто изменяющих объекты пользователей.<br>
Из шаблона получите URL с помощь ``{% url 'service:public:history-authors_top' as authors_url %}``. Метод возвращает шаблон history/authors_top.html, в котором доступна переменная ``authors``.

* ``HistoryProvider.timeline(request, consumer_types, root)`` - вывод временной линии изменений для объектов определенного типа. <br>
Для получения URL'а в шаблоне, используйте ``{% url 'service:public:history-timeline' document, profile history_url %}`` - в данном примере будет сгенерирован список изменений для объектов типа ``Document`` и ``Profile``. Метод возвращает шаблон spicy.history/rubric_timeline.html, в котором доступны переменные ``paginator``, ``consumer_types`` и ``root``. Описание переменных смотрите [ниже](./README.md#Список-переменных-шаблонов-spicyhistory).

В spicy.history есть шаблоны, которые используются по умолчанию, для отображения результатов этих методов. Вы можете переопределить их или дополнить. Подробнее про переопределение дефолтных шаблонов читайте в [документации spicy.core.siteskin](https://github.com/spicycms/spicy.core/blob/develop/docs/siteskin/README.rst#Переопределяем-шаблон-модуля-spicycms). 


#### Список переменных шаблонов spicy.history

* nav - объект [NavigationFilter](https://github.com/spicycms/spicy.core/blob/8436b2677448cc1cd398fc37d4330edfb8f5170a/src/spicy/utils/filters.py#L12), реализует фильтрацию списка объектов по условиям и ограничения из GET-запроса
* objects_list - список объектов, на текущей странице пажинатора
* paginator - объект пажинатора
* consumer - объект указанного типа, для которого будет получена история именений
* consumer_type_id - id ContentType для объекта
* fields - поля, по которым возвращается списк изменений
* prov - провайдер сервиса истории измений
* status - статус обработки AJAX запроса
* message - сообщение после обработки AJAX запроса. Успех либо неудача
* next_url - URL для редиректа после успешного исполнения AJAX запроса
* authors - спискок авторов, которые наиболее часто вносят изменения в отслеживаемые объекты
* root - используется для истории изменений объектов Xtag модуля [spicy.xtag](https://gitlab.com/spicycms.com/spicy.xtag#spicyxtag), позволяет указать, начиная с какого родительского тега, рассматривать объекты тегов

### Refactoring
Не используются:

* Настройка defaults.py ``TIMELINE_PAGE_DAYS``
* Настройка defaults.py ``TIMELINE_FEED_DAYS``




