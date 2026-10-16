"""The home page opens and shows the app name."""


def test_home_page_opens(client):
    response = client.get("/")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "mymotoworks" in page
    assert "Jaryl's Motoworks" in page


def test_home_page_has_theme_button(client):
    page = client.get("/").get_data(as_text=True)
    assert "data-theme-toggle" in page
