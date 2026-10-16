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
    assert tab_links(page(admin, "/dashboard")) == ["Home", "Sell", "Sales", "Items", "Users"]
    assert tab_links(page(login("staff1"), "/sell")) == ["Sell", "Sales", "Items"]


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


def test_items_search_stays_and_filters_are_in_an_expandable_panel(admin):
    html = page(admin, "/items")
    assert 'id="search"' in html and 'data-bs-target="#filter-panel"' in html
    panel = html.split('id="filter-panel"')[1].split("</main>")[0]
    assert 'id="low-only"' in panel and 'id="show-inactive"' in panel
    # The switches are no longer next to the search box.
    before_panel = html.split('id="filter-panel"')[0]
    assert 'id="low-only"' not in before_panel and 'id="show-inactive"' not in before_panel


def test_staff_filter_panel_has_low_stock_but_no_deactivated_switch():
    html = page(login("staff1"), "/items")
    panel = html.split('id="filter-panel"')[1].split("</main>")[0]
    assert 'id="low-only"' in panel
    assert "show-inactive" not in html


def test_items_search_and_filter_do_not_float(admin):
    assert "sticky" not in page(admin, "/items")


def test_the_sell_page_shows_the_item_list_with_a_filter_and_two_tabs(admin):
    html = page(login("staff1"), "/sell")
    for element in ('id="item-filter"', 'id="item-list"', 'id="tab-items"', 'id="tab-cart"', 'id="panel-items"',
                    'id="panel-cart"'):
        assert element in html, element
    assert 'id="results"' not in html  # the old search-first results box is gone


def test_the_sell_list_is_a_flat_list_in_its_own_scroll_box(admin):
    html = page(login("staff1"), "/sell")
    assert 'id="item-scroll"' in html and 'id="items-count"' in html
    # The list sits inside the box: nothing closes between the box opening and the list opening.
    between = html.split('id="item-scroll"')[1].split('id="item-list"')[0]
    assert "</div>" not in between


def test_the_items_page_has_a_restock_button_for_the_admin_only(admin):
    assert 'href="/restock"' in page(admin, "/items")
    assert 'href="/restock"' not in page(login("staff1"), "/items")
