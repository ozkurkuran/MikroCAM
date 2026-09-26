"""Present core identity and explain the unavailable product update channel."""
from collections.abc import Callable
import gettext
from html import escape

from mikrocam.core import identity


def window_title(project: str = '', *, engine: str = '', architecture: str = '') -> str:
    """Return plain window text; project names are never interpreted as markup."""
    title = f'{identity.NAME} {identity.VERSION}'
    if architecture:
        title += f' - {architecture}'
    if engine:
        title += f' - [{engine}]'
    if project:
        title += f'    {project}'
    return title


def about_heading(translate: Callable[[str], str] = gettext.gettext) -> str:
    """Return the product heading and official project links as escaped HTML."""
    links = ((identity.REPOSITORY_URL, 'Development'),
             (identity.RELEASES_URL, 'Releases'), (identity.ISSUES_URL, 'Issue tracker'))
    return (f'<font size=8><b>{escape(identity.NAME)}</b></font><br>'
            f'{escape(translate(identity.DESCRIPTION))}<br><br>' +
            '<br>'.join(f'<a href="{escape(url, quote=True)}"><b>{escape(translate(label))}</b></a>'
                        for url, label in links))


def about_description(architecture: str, translate: Callable[[str], str] = gettext.gettext) -> str:
    """Keep product and original source copyrights separate from dependency terms."""
    lines = (f'{identity.NAME} {identity.VERSION} ({identity.RELEASE_DATE}) - {architecture}',
             identity.COPYRIGHT, *identity.UPSTREAM_COPYRIGHTS)
    return ('<br>'.join(escape(line) for line in lines) + '<br>' +
            f'<a href="{escape(identity.UPSTREAM_URL, quote=True)}">{escape(translate("FlatCAM / Evo upstream"))}</a>' +
            '<br><br>' + escape(translate(identity.DEPENDENCY_NOTICE)))


def updates_unavailable(app: object, translate: Callable[[str], str] = gettext.gettext,
                        *, notify: bool = True) -> None:
    """Block inherited product updater entry points without changing saved preferences."""
    if notify:
        signal = getattr(app, 'inform', None)
        if signal is not None:
            signal.emit('[WARNING_NOTCL] %s' % update_unavailable_message(translate))


def update_unavailable_message(translate: Callable[[str], str] = gettext.gettext) -> str:
    """Use the authoritative product name in the translated update explanation."""
    return translate('%s updates are not available. The inherited Evo update channel is disabled.') % identity.NAME


def disable_update_controls(ui: object, translate: Callable[[str], str] = gettext.gettext) -> None:
    """Disable existing actions/widgets and describe the product boundary."""
    group = getattr(getattr(ui, 'general_pref_form', None), 'general_app_group', ui)
    for owner, names in ((ui, ('menuhelp_check_updates', 'menuhelp_revert_update')),
                         (group, ('version_check_cb', 'prepare_update_files_btn'))):
        for name in names:
            control = getattr(owner, name, None)
            if control is not None:
                control.setEnabled(False)
                control.setToolTip(update_unavailable_message(translate))


def finish_unavailable_update(app: object, translate: Callable[[str], str] = gettext.gettext) -> None:
    """Clear inherited pending download state while refusing to launch its installer."""
    app._update_in_progress = False
    close = getattr(app, '_close_update_progress', None)
    if callable(close):
        close()
    updates_unavailable(app, translate)
