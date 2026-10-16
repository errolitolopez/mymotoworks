"""All SQL lives here, one class per kind of data."""

from mymotoworks.repositories.items import ItemRepository
from mymotoworks.repositories.reports import ReportRepository
from mymotoworks.repositories.restocks import RestockRepository
from mymotoworks.repositories.sales import SaleRepository
from mymotoworks.repositories.settings import SettingsRepository
from mymotoworks.repositories.stock import StockRepository
from mymotoworks.repositories.users import UserRepository

__all__ = ["ItemRepository", "ReportRepository", "RestockRepository", "SaleRepository", "SettingsRepository", "StockRepository",
           "UserRepository"]
