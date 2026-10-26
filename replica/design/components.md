# Компоненты (спецификации)

Общее: цвета и размеры только через токены (`bg-surface text-muted`, не hex). Иконки — Lucide. Фокус: `outline: 2px solid var(--focus-ring); outline-offset: 2px` на всех интерактивных элементах (`:focus-visible`). База: Radix UI для диалогов, меню, вкладок; CodeMirror 6 для редактора.
Состояния по умолчанию: default, hover, active, focus-visible, disabled, loading, error, empty — ниже указаны только отличия.

| Компонент | Варианты / размеры | Состояния и токены | Доступность | Экраны |
|---|---|---|---|---|
| **Button** | primary (`accent`/`on-accent`), secondary (`surface-2`), ghost, danger; sm/md | hover: затемнение фона; disabled: opacity .5, нет курсора; loading: спиннер, `aria-busy` | настоящий `<button>`, у иконочных `aria-label` | S01, S12 |
| **IconButton** | 28×28 / 32×32 | как Button ghost | обязателен `aria-label` + tooltip | S02, S03 |
| **TextInput** | обычный, поиск (с иконкой) | граница `border-input`, error: `danger` + текст ошибки | `<label>` или `aria-label`, `aria-invalid`, `aria-describedby` | S05, S06, S11 |
| **Sidebar** | левый 260px, правый 300px; сворачивается | граница `border`, фон `surface` | `<nav>`/`<aside>` с `aria-label`; сворачивание кнопкой, `aria-expanded` | S02 |
| **FileTree** | папки раскрываются; элемент: заметка/папка | выбранный: `surface-2`; переименование: input на месте; drag-over: подсветка `accent`; empty: «Пока нет заметок» + кнопка | `role="tree"`/`treeitem`, стрелки, Enter, F2 переименовать, Delete | S03 |
| **Tabs** | открытая, закрепляемая; закрытие × | активная: `bg`, нижняя линия `accent`; изменённая: точка | `role="tablist"`, Ctrl+Tab, Ctrl+W | S02 |
| **Editor** | режимы Source / Live Preview / Reading; ширина `editor-max` | шрифт `sans` (preview), `mono` (source); loading: скелетон; error: баннер «Не сохранено» + повтор; long text: виртуализация CodeMirror | `role="textbox"`, `aria-multiline`; все действия доступны с клавиатуры | S04 |
| **LinkToken** | `[[ссылка]]`: существующая (`link`), несуществующая (`link-missing`, пунктир) | hover: подсказка с превью; Ctrl+клик — в новой вкладке | `<a>` в режиме чтения, цвет не единственный признак (пунктир) | S04 |
| **LinkSuggest** | выпадающий список под курсором | выбранный пункт `surface-2`; empty: «Создать «текст»» | `role="listbox"`/`option`, `aria-activedescendant` | S04 |
| **CommandModal** | switcher (S05), палитра команд (S11) | `shadow-modal`, затемнение фона; empty: «Ничего не найдено»; создание: пункт «Создать…» | Radix Dialog, фокус-ловушка, Esc закрывает, стрелки + Enter | S05, S11 |
| **SearchResults** | группа по заметкам, фрагмент с подсветкой `mark` | loading: скелетон; empty: «Ничего не найдено» | `<ul>`, подсветка не только цветом (`<mark>` + фон) | S06 |
| **BacklinkList** | linked / unlinked mentions; сворачиваемые секции | empty: «Ссылок на эту заметку нет» | `<details>`/`aria-expanded` | S07 |
| **TagList** | плоский / вложенный (дерево); бейдж со счётчиком | выбранный: `accent`; empty: «Тегов пока нет» | `<button>` на каждый тег | S09 |
| **GraphCanvas** | глобальный / локальный; панель фильтров | узел `graph-node`, выбранный `accent`, ребро `graph-edge`; loading: «Строим граф…»; empty: «Свяжите заметки через [[ ]]»; >2000 узлов: предупреждение | canvas не читается скринридером → дублирующий `<ul>` с узлами за кнопкой «Список»; зум кнопками +/− и клавишами | S08 |
| **Toast** | info, success, error | `role="status"` / error `role="alert"`, автоскрытие 5с (не для error) | `aria-live` | везде |
| **ContextMenu** | пункты с иконками, разделители | Radix ContextMenu | стрелки, Esc | S03 |
| **ThemeToggle** | light / dark / system | сохраняется в `setting` | `aria-pressed`/radio group | S12 |

## Раскладка
Три колонки: левый сайдбар 260px | область вкладок + редактор (центр, текст ≤760px) | правый сайдбар 300px (обратные ссылки, теги). Шапка 40px. Ниже `bp-lg` (1100px) правый сайдбар прячется в выдвижную панель; ниже `bp-md` (768px) левый тоже выдвижной, один основной экран.

## Проверка контраста (WCAG AA)
32 пары (16 в светлой, 16 в тёмной теме): текст/фон ≥4.5:1, границы полей и кольцо фокуса ≥3:1. Провалов 0.
