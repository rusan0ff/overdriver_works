judge_core - критериальная оценка, чистая стандартная библиотека Python.
Автор: overdriver, 2026-11-03. Живёт только в <ROOT>.

Зачем: посчитать взвешенную оценку 0..100 по набору критериев и честно
показать, где данных нет, вместо того чтобы выдать красивый, но ложный ноль.

Запуск тестов:
  cd <ROOT>
  python -m unittest judge_core.test_scorer -v

Пример:
  from judge_core.scorer import Scorer, Criterion
  s = Scorer([Criterion.of("logic", 2, 10), Criterion.of("style", 1, 5)])
  r = s.score({"logic": 8, "style": 4})
  print(r.total)        # 80.00
  print(r.complete)     # True
  print(r.errors)       # []
  print(r.to_csv())

Неполные данные:
  r = s.score({"logic": 11})   # значение вне диапазона
  print(r.total)       # None  <- не 0.00
  print(r.errors)      # ["'logic' out of range 0..10 (got 11)", "missing value for 'style'"]
  print(r.complete)    # False

Правила, которых я держался:
  1. Плохие ДАННЫЕ сообщаются (errors), плохая КОНФИГУРАЦИЯ падает (ScoringConfigError).
  2. Округление только в самом конце — порядок критериев не влияет на итог.
  3. Нет данных — это None и complete=False, а не оценка. Ноль врёт.

Ограничения (честно):
  - Нет сохранения в БД, нет UI. Только расчёт и CSV.
  - Тексты не оценивает — оценивает уже выставленные баллы по критериям.
  - Зависимостей нет вообще, поэтому и запускается на голом Python 3.14.
