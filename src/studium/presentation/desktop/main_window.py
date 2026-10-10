"""Studium Windows MVP shell with local workspaces."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from studium.presentation.desktop.components import (
    hint,
    panel,
    run_action,
    selected,
    table,
)
from studium.presentation.desktop.dialogs import (
    CourseDialog,
    CoursesDialog,
    GroupDialog,
    TermDialog,
)
from studium.presentation.desktop.icons import icon
from studium.presentation.desktop.messages import TEXT
from studium.presentation.desktop.models import TableModel
from studium.presentation.desktop.navigation import NavigationStack, Sidebar, present_detail
from studium.presentation.desktop.pages import GroupsPage
from studium.presentation.desktop.theme import apply_theme, resize_to_screen
from studium.presentation.desktop.visuals import HomeTile, RecentGroupDelegate, text_label


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        apply_theme()
        self.service = None
        self.setWindowTitle(TEXT["app"])
        self.setMinimumSize(960, 620)
        resize_to_screen(self, 1240, 780)
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        sidebar_surface = QWidget()
        sidebar_surface.setObjectName("sidebar")
        sidebar_surface.setFixedWidth(232)
        sidebar = QVBoxLayout(sidebar_surface)
        sidebar.setContentsMargins(16, 28, 16, 20)
        sidebar.setSpacing(16)
        logo = QLabel(TEXT["app"])
        logo.setProperty("role", "brand")
        sidebar.addWidget(logo)
        self.navigation = Sidebar()
        self.navigation.groupSelected.connect(self.open_sidebar_group)
        self.navigation.courseSelected.connect(self.open_sidebar_course)
        self.navigation.librarySelected.connect(self.open_sidebar_library)
        self.navigation.expansionChanged.connect(self.save_sidebar_state)
        sidebar.addWidget(self.navigation)
        self.help_button = QPushButton("Справка")
        self.help_button.setProperty("role", "quiet")
        self.help_button.clicked.connect(lambda: self.open_help())
        sidebar.addWidget(self.help_button)
        self.settings_button = QPushButton(TEXT["settings"])
        self.settings_button.setIcon(icon("settings"))
        self.settings_button.setProperty("role", "quiet")
        self.settings_button.setCheckable(True)
        self.settings_button.clicked.connect(self.show_settings)
        sidebar.addWidget(self.settings_button)
        sidebar.addWidget(text_label("Локальное рабочее пространство", "caption"))
        outer.addWidget(sidebar_surface)
        workspace = QVBoxLayout()
        workspace.setContentsMargins(32, 20, 32, 24)
        workspace.setSpacing(20)
        self.term_combo = QComboBox()
        self.term_combo.setAccessibleName("Учебный период")
        self.term_combo.setMinimumWidth(220)
        self.term_combo.setMaximumWidth(360)
        self.term_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.term_combo.setMinimumContentsLength(18)
        self.term_combo.currentIndexChanged.connect(lambda _: run_action(self, self.select_term))
        self.pages = QStackedWidget()
        self.pages.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.router = NavigationStack(self.pages, self)
        route_header = QHBoxLayout()
        self.back_button = QPushButton("Назад")
        self.back_button.setIcon(icon("back"))
        self.back_button.setProperty("role", "quiet")
        self.back_button.clicked.connect(self.router.back)
        route_header.addWidget(self.back_button)
        self.breadcrumb = QLabel()
        self.breadcrumb.setObjectName("breadcrumb")
        self.breadcrumb.setWordWrap(True)
        route_header.addWidget(self.breadcrumb, 1)
        route_header.addWidget(self.term_combo)
        workspace.addLayout(route_header)
        self.router.changed.connect(self.update_route_header)
        workspace.addWidget(self.pages)
        outer.addLayout(workspace, 1)
        overview, layout = panel()
        overview_layout = layout
        overview_layout.setContentsMargins(0, 16, 0, 0)
        overview_layout.addWidget(text_label("Добро пожаловать", "heading"))
        self.welcome = text_label(TEXT["empty_start"])
        overview_layout.addWidget(self.welcome)
        self.overview_stack = QStackedWidget()
        layout.addWidget(self.overview_stack)
        self.onboarding, start_layout = panel()
        title = hint(start_layout, TEXT["onboarding_heading"])
        title.setProperty("role", "heading")
        hint(start_layout, TEXT["onboarding_hint"])
        self.steps = []
        for key, action in [
            ("step_term", self.create_term),
            ("step_course", self.create_course),
            ("step_group", self.setup_group),
        ]:
            button = QPushButton(TEXT[key])
            button.clicked.connect(lambda _checked=False, action=action: run_action(self, action))
            start_layout.addWidget(button)
            self.steps.append(button)
        start_layout.addStretch()
        self.overview_stack.addWidget(self.onboarding)
        normal, layout = panel()
        layout.setContentsMargins(0, 16, 0, 0)
        self.overview_stack.addWidget(normal)
        cards = QHBoxLayout()
        cards.setSpacing(16)
        self.home_tiles = {}
        for label, description, index in (
            ("Работа", "Журналы, группы и текущая деятельность", 1),
            ("Дисциплины", "Рабочие программы, темы, навыки и планы", 2),
            ("Библиотека", "Задачи, учебные материалы и литература", 3),
        ):
            card = HomeTile(label, description, {1: "work", 2: "course", 3: "library"}[index])
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            card.clicked.connect(lambda _=False, index=index: self.navigation.setCurrentRow(index))
            cards.addWidget(card, 1)
            self.home_tiles[index] = card
        overview_layout.insertLayout(2, cards)
        resume_surface = QFrame()
        resume_surface.setProperty("role", "surface")
        resume_layout = QVBoxLayout(resume_surface)
        resume_layout.setContentsMargins(24, 20, 24, 20)
        resume_layout.setSpacing(8)
        self.continue_label = text_label("Продолжить работу", "subheading")
        resume_layout.addWidget(self.continue_label)
        self.continue_button = QPushButton()
        self.continue_button.setProperty("role", "resumeGroup")
        self.continue_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        continue_layout = QVBoxLayout(self.continue_button)
        self.continue_context = text_label("", "subheading")
        self.continue_context.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        continue_layout.addWidget(self.continue_context)
        self.continue_button.clicked.connect(self.resume_work)
        resume_layout.addWidget(self.continue_button)
        resume_layout.addWidget(text_label("Недавние:", "caption"))
        self.overview_model = TableModel(
            [
                (TEXT["group"], lambda c: c.group.number),
                (TEXT["course"], lambda c: c.course.name),
                (TEXT["period"], lambda c: c.term.name),
            ]
        )
        self.overview_view = table(self.overview_model)
        self.overview_view.horizontalHeader().hide()
        RecentGroupDelegate.configure(self.overview_view)
        self.overview_view.setMaximumHeight(150)
        self.overview_view.setMouseTracking(True)
        self.overview_view.clicked.connect(lambda _: run_action(self, self.open_overview_group))
        self.overview_view.activated.connect(lambda _: run_action(self, self.open_overview_group))
        resume_layout.addWidget(self.overview_view)
        layout.addWidget(resume_surface)
        layout.addStretch()
        home_scroll = QScrollArea()
        home_scroll.setWidgetResizable(True)
        home_scroll.setWidget(overview)
        self.pages.addWidget(home_scroll)
        self.groups_page = GroupsPage(self)
        self.pages.addWidget(self.groups_page)
        self.works_page = self.groups_page.works_page
        self.questions_page = self.groups_page.questions
        from studium.presentation.desktop.programs import DisciplinesPage

        self.disciplines_page = DisciplinesPage(self)
        self.pages.addWidget(self.disciplines_page)
        from studium.presentation.desktop.library import LibraryPage

        self.library_page = LibraryPage(self)
        self.pages.addWidget(self.library_page)
        from studium.presentation.desktop.reports import ReportsPage

        self.reports_page = ReportsPage(self)
        self.pages.addWidget(self.reports_page)
        settings, layout = panel()
        self.settings_page = settings
        hint(layout, "Настройки").setProperty("role", "heading")
        hint(layout, TEXT["settings_hint"])
        self.settings_form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName("Тема оформления")
        self.theme_combo.addItem("Светлая", "light")
        self.theme_combo.addItem("Тёмная", "dark")
        self.settings_form.addRow("Тема", self.theme_combo)
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        layout.addLayout(self.settings_form)
        from studium.presentation.desktop.backup import BackupPanel

        self.backup_panel = BackupPanel(self)
        layout.addWidget(self.backup_panel)
        layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(settings)
        self.settings_page = scroll
        self.pages.addWidget(scroll)
        from studium.presentation.desktop.help_center import HelpCenter

        self.help_page = HelpCenter(self)
        self.pages.addWidget(self.help_page)
        self.navigation.currentRowChanged.connect(self.navigate)
        self.navigation.setCurrentRow(0)

    def initialize(self, service, diagnostics):
        self.service = service
        self.data_directory = diagnostics.data_directory
        self.navigation.restore_expansion(service.sidebar_state())
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(service.preferred_theme()))
        self.theme_combo.blockSignals(False)
        apply_theme(service.preferred_theme())
        self.questions_page.service = service
        for key in [
            "db_path",
            "data_directory",
            "app_version",
            "schema_version",
            "python_version",
            "qt_version",
        ]:
            attr = "database_path" if key == "db_path" else key
            label = QLabel(str(getattr(diagnostics, attr)))
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.settings_form.addRow(TEXT[key], label)
        self.refresh()

    def navigate(self, index):
        if index >= 0:
            self.router.root(self.pages.widget(index), self.navigation.topLevelItem(index).text(0))
            self.settings_button.setChecked(False)
            if index == 1:
                self.groups_page.back()
            if index == 0 and self.service:
                run_action(self, self.refresh)
            if index == 3 and self.service:
                run_action(self, self.library_page.refresh)
            if index == 2 and self.service:
                run_action(self, self.disciplines_page.refresh)
            if index == 4 and self.service:
                run_action(self, self.reports_page.refresh)

    def update_route_header(self):
        self.back_button.setVisible(len(self.router.routes) > 1)
        if self.router.routes:
            route = self.router.routes[-1]
            root = self.router.routes[0].page
            mode = 1 if route.page is self.groups_page else self.pages.indexOf(root)
            if 0 <= mode < self.navigation.count():
                self.navigation.blockSignals(True)
                current = self.navigation.currentItem()
                if current is None or (
                    current.parent() or current
                ) is not self.navigation.topLevelItem(mode):
                    self.navigation.setCurrentItem(self.navigation.topLevelItem(mode))
                self.navigation.blockSignals(False)
        titles = [route.title for route in self.router.routes]
        if self.router.routes and self.router.routes[0].page is self.groups_page:
            context = self.groups_page.context()
            if context and self.groups_page.current_group:
                titles = [context.course.name, context.term.name, context.group.number] + titles[2:]
        self.breadcrumb.setText("  /  ".join(titles))

    def open_sidebar_group(self, context):
        self.router.root(self.groups_page, TEXT["groups"])
        self.open_group_context(context)

    def open_group_context(self, context):
        if self.router.routes:
            self.router.routes[-1].refresh = self.refresh
        self.groups_page.open_group(context.group)
        for i in range(self.groups_page.contexts.count()):
            if self.groups_page.contexts.itemData(i).offering.id == context.offering.id:
                self.groups_page.contexts.setCurrentIndex(i)
                break
        self.groups_page.tabs.setCurrentIndex(0)

    def open_sidebar_course(self, course):
        from studium.presentation.desktop.programs import DisciplinePage

        self.router.root(self.disciplines_page, "Дисциплины")
        self.service.remember_course(course.id)
        self.router.push(DisciplinePage(self, course), course.name)

    def open_sidebar_library(self, kind):
        self.router.root(self.library_page, "Библиотека")
        self.library_page.select_section(kind)

    def save_sidebar_state(self):
        if self.service:
            run_action(
                self, lambda: self.service.save_sidebar_state(self.navigation.expansion_state())
            )

    def show_settings(self):
        self.navigation.setCurrentRow(-1)
        self.router.root(self.settings_page, TEXT["settings"])
        self.settings_button.setChecked(True)

    def closeEvent(self, event):
        self.backup_panel.cancel_active()
        super().closeEvent(event)

    def open_help(self, article_id="getting-started"):
        self.navigation.setCurrentRow(-1)
        self.settings_button.setChecked(False)
        self.router.root(self.help_page, "Справка")
        self.help_page.open_article(article_id)

    def refresh(self):
        terms = self.service.list_terms()
        active = self.service.active_term()
        self.term_combo.blockSignals(True)
        self.term_combo.clear()
        for term in terms:
            self.term_combo.addItem(term.name, term)
        self.term_combo.insertSeparator(self.term_combo.count())
        self.term_combo.addItem("Управление периодами…", "manage")
        if active:
            self.term_combo.setCurrentIndex(
                next(i for i, t in enumerate(terms) if t.id == active.id)
            )
        else:
            self.term_combo.setPlaceholderText(TEXT["period_empty"])
        self.term_combo.blockSignals(False)
        contexts = self.service.list_offerings(term_id=active.id) if active else []
        courses = self.service.list_courses()
        recent = self.service.recent_offering_ids()
        contexts = sorted(
            contexts,
            key=lambda c: recent.index(c.offering.id) if c.offering.id in recent else len(recent),
        )
        self.navigation.set_groups([c for c in contexts if c.offering.id in recent])
        recent_courses = self.service.recent_course_ids()
        self.navigation.set_courses(
            sorted(
                courses,
                key=lambda c: (
                    recent_courses.index(c.id) if c.id in recent_courses else len(recent_courses)
                ),
            )[:4]
        )
        self.home_tiles[1].detail.setText(f"Групп в периоде: {len(contexts)}")
        self.home_tiles[2].detail.setText(f"Дисциплин: {len(courses)}")
        self.home_tiles[3].detail.setText("Задачи · материалы · источники")
        self.overview_stack.setCurrentIndex(1 if contexts else 0)
        for button, complete in zip(
            self.steps, [bool(active), bool(courses), bool(contexts)], strict=True
        ):
            button.setEnabled(not complete)
            button.setProperty("primary", not complete)
        self.steps[1].setEnabled(bool(active) and not courses)
        self.steps[2].setEnabled(bool(active) and bool(courses) and not contexts)
        self.overview_model.replace_rows(contexts[1:5])
        self.overview_view.setFixedHeight(max(1, min(4, len(contexts) - 1)) * 58 + 2)
        recent_id = self.service.recent_offering_id()
        self.resume_context = next(
            (c for c in contexts if c.offering.id == recent_id), contexts[0] if contexts else None
        )
        self.continue_button.setEnabled(self.resume_context is not None)
        if self.resume_context:
            context = self.resume_context
            program = self.service.program_for_offering(context.offering.id)
            from studium.presentation.desktop.workflow_widgets import week_label

            week = self.service.current_program_week(context.offering.id)
            module = (
                next(
                    (
                        m
                        for m in self.service.list_program_modules(program.id)
                        if week and m.start_week <= week.value <= m.end_week
                    ),
                    None,
                )
                if program
                else None
            )
            self.continue_context.setText(
                f"{context.group.number} · {context.course.name}\n{week_label(week)}"
                + (f" · {module.title}" if module else "")
            )
            self.continue_button.setAccessibleName(f"Открыть журнал {context.group.number}")
        self.welcome.setText(TEXT["overview_hint"] if contexts else TEXT["empty_start"])
        self.groups_page.refresh()
        self.library_page.refresh()
        self.disciplines_page.refresh()
        if self.pages.currentWidget() is self.reports_page:
            self.reports_page.refresh()
        else:
            self.reports_page.invalidate()

    def resume_work(self):
        if self.resume_context:
            self.open_group_context(self.resume_context)

    def change_theme(self):
        if self.service:
            theme = self.theme_combo.currentData()
            self.service.select_theme(theme)
            apply_theme(theme)

    def select_term(self):
        term = self.term_combo.currentData()
        if term == "manage" and self.service:
            from studium.presentation.desktop.periods import PeriodManager

            PeriodManager(self).exec()
            self.refresh()
            return
        if self.service and term:
            self.service.select_term(term.id)
            self.refresh()

    def create_term(self):
        if (
            TermDialog(lambda v: self.service.create_term(**v), parent=self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def edit_term(self):
        term = self.term_combo.currentData()
        if (
            term
            and TermDialog(lambda v: self.service.update_term(term, **v), term, self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def manage_courses(self):
        present_detail(CoursesDialog(self.service, self), self, refresh=self.refresh)

    def create_course(self):
        if (
            CourseDialog(lambda v: self.service.create_course(**v), parent=self).exec()
            == QDialog.DialogCode.Accepted
        ):
            self.refresh()

    def setup_group(self):
        """The last onboarding step also establishes the existing offering context."""
        created = []

        def save(values):
            created.append(self.service.create_group(**values))

        if GroupDialog(save, parent=self).exec() != QDialog.DialogCode.Accepted:
            return
        self.refresh()
        group = created[0]
        self.navigation.setCurrentRow(1)
        self.groups_page.open_group(group)
        self.groups_page.add_course()
        self.refresh()

    def open_overview_group(self):
        context = selected(self.overview_view)
        if context:
            self.open_group_context(context)
