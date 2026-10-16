"""Mobile-first page structure: the bottom tab bar, one user menu, full-screen modals on phones."""

from conftest import login


def page(client, path):
    response = client.get(path)
    assert response.status_code == 200, path
    return response.get_data(as_text=True)


def tab_links(html):
    """The link texts inside the bottom tab bar."""
    bar = html.split('class="tabbar')[1].split("</nav>")[0]
    return [part.split("<")[0].strip() for part in bar.split('<span class="tab-label">')[1:]]


def test_viewport_covers_the_notch_area(client):
    assert "viewport-fit=cover" in client.get("/login").get_data(as_text=True)


def test_logged_in_pages_have_a_bottom_tab_bar(admin):
    for path in ("/dashboard", "/items", "/users"):
        assert 'class="tabbar' in page(admin, path), path


def test_tab_bar_follows_the_role(admin):
    assert tab_links(page(admin, "/dashboard")) == ["Home", "Items", "Users"]
    assert tab_links(page(login("staff1"), "/dashboard")) == ["Home", "Items"]


def test_the_current_page_tab_is_marked(admin):
    html = page(admin, "/items")
    assert 'aria-current="page"' in html.split('class="tabbar')[1].split("</nav>")[0]


def test_login_and_password_pages_have_no_tab_bar(client):
    assert 'class="tabbar' not in page(client, "/login")
    staff = login("staff1")
    assert 'class="tabbar' not in page(staff, "/change-password")


def test_one_user_menu_with_password_theme_and_logout(admin):
    html = page(admin, "/dashboard")
    assert html.count('id="logout-button"') == 1
    menu = html.split('class="dropdown-menu')[1].split("</ul>")[0]
    assert "Password" in menu and "data-theme-toggle" in menu and "Logout" in menu


def test_big_forms_are_full_screen_on_phones(admin):
    assert "modal-fullscreen-sm-down" in page(admin, "/items")
    assert "modal-fullscreen-sm-down" in page(admin, "/users")
