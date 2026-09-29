"""Небольшие частотные словари для запасного детектора.

На macOS основным источником служит системная проверка орфографии
(NSSpellChecker); эти списки нужны, когда она недоступна, и для построения
биграммной модели «правдоподобности» слова.
"""

RU_WORDS = """
и в не на я что тот быть с он а весь это как она по но они к у ты из мы за
вы так же от сказать этот который мочь человек о один еще бы такой только
себя свой какой когда уже для вот кто да говорить год знать мой до или если
время рука нет самый ни стать большой даже другой наш сам ну под где дело
есть сейчас раз день жизнь потом ничто очень хотеть хорошо лишь первый
новый тоже думать глаз теперь будет через работа слово место лицо друг
всегда жить почему после надо здесь можно спасибо пожалуйста привет пока
вопрос ответ сегодня завтра вчера утро вечер ночь неделя месяц минута
час деньги город страна дом улица машина компьютер телефон письмо сообщение
проект задача ошибка файл папка программа приложение сайт страница текст
клавиатура раскладка язык русский английский буква слово строка
хорошо плохо отлично нормально понятно конечно точно просто быстро
медленно сразу давно скоро снова вместе потому поэтому также тогда
сделать делать написать писать читать прочитать смотреть посмотреть
видеть понимать понять помочь помощь работать работаю знаю думаю могу
хочу надо нужно нужен нужна будем будет было были была есть нет
какой какая какое какие кто что где когда куда откуда зачем сколько
мама папа брат сестра семья ребенок дети муж жена друзья коллега
встреча звонок письмо время начало конец середина часть сторона
вода еда чай кофе хлеб молоко магазин деньги цена рубль доллар
красивый новый старый большой маленький важный интересный главный
добрый доброе утро день вечер спокойной ночи всего доброго увидимся
давай давайте создадим сделаем посмотрим попробуем исправить исправление
пользователь забыл переключить скрипт фон фоновый устройство
как дела что делаешь где ты когда будешь
""".split()

EN_WORDS = """
the be to of and a in that have i it for not on with he as you do at this
but his by from they we say her she or an will my one all would there their
what so up out if about who get which go me when make can like time no just
him know take people into year your good some could them see other than then
now look only come its over think also back after use two how our work first
well way even new want because any these give day most us is are was were
hello hi thanks thank please yes okay ok sorry world today tomorrow yesterday
morning evening night week month minute hour money city country house street
car computer phone letter message project task error file folder program
application app site page text keyboard layout language russian english
letter word line good bad great fine sure right exactly simple quick fast
slow soon again together because therefore also then make do write read
watch see understand help working know think can want need will should
where why how what who which when mother father brother sister family child
children friend meeting call start end middle part side water food tea
coffee bread milk shop price beautiful old big small important interesting
main kind let lets create fix switch script background device user forgot
test code commit push pull branch merge review function class return import
""".split()


def _bigrams(word):
    w = f"^{word}$"
    return (w[i:i + 2] for i in range(len(w) - 1))


def build_bigrams(words):
    seen = set()
    for w in words:
        seen.update(_bigrams(w.lower()))
    return frozenset(seen)


RU_BIGRAMS = build_bigrams(RU_WORDS)
EN_BIGRAMS = build_bigrams(EN_WORDS)
RU_SET = frozenset(RU_WORDS)
EN_SET = frozenset(EN_WORDS)
