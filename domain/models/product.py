# # app/domain/models/product.py
# from dataclasses import dataclass
# from typing import Optional
# from datetime import date
# from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, Boolean
# from sqlalchemy.orm import declarative_base

# Base = declarative_base()


# # SQLAlchemy ORMモデル
# class ProductORM(Base):
#     """製品モデル - SQLAlchemy ORM (DBアクセス用)"""
#     __tablename__ = "products"
    
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     data_no = Column(Integer)
#     factory = Column(String(10))
#     client_code = Column(Integer)
#     calculation_date = Column(Date)
#     production_complete_date = Column(Date)
#     modified_factory = Column(String(10))
#     product_category = Column(String(10))
#     product_code = Column(String(20))
#     ac_code = Column(String(10))
#     processing_content = Column(String(100))
#     product_name = Column(String(100))
#     delivery_location = Column(String(50))
#     box_type = Column(String(10))
#     capacity = Column(Integer)
#     grouping_category = Column(String(10))
#     form_category = Column(String(10))
#     inspection_category = Column(String(10))
#     ordering_category = Column(String(10))
#     regular_replenishment_category = Column(String(10))
#     lead_time = Column(Integer)
#     fixed_point_days = Column(Integer)
#     shipping_factory = Column(String(10))
#     client_product_code = Column(String(50))
#     purchasing_org = Column(String(10))
#     item_group = Column(String(10))
#     processing_type = Column(String(10))
#     inventory_transfer_category = Column(String(10))
#     created_at = Column(TIMESTAMP)
#     container_width = Column(Integer)
#     container_depth = Column(Integer)
#     container_height = Column(Integer)
#     stackable = Column(Boolean, default=True)
#     used_container_id = Column(Integer)
#     can_advance = Column(Boolean, default=False)


# # Dataclass (ビジネスロジック用)
# @dataclass
# class Product:
#     """製品モデル - Dataclass (ビジネスロジック用)"""
#     id: int
#     data_no: Optional[int] = None
#     factory: Optional[str] = None
#     client_code: Optional[int] = None
#     calculation_date: Optional[date] = None
#     production_complete_date: Optional[date] = None
#     modified_factory: Optional[str] = None
#     product_category: Optional[str] = None
#     product_code: Optional[str] = None
#     ac_code: Optional[str] = None
#     processing_content: Optional[str] = None
#     product_name: Optional[str] = None
#     delivery_location: Optional[str] = None
#     box_type: Optional[str] = None
#     capacity: Optional[int] = None
#     grouping_category: Optional[str] = None
#     form_category: Optional[str] = None
#     inspection_category: Optional[str] = None
#     ordering_category: Optional[str] = None
#     regular_replenishment_category: Optional[str] = None
#     lead_time: Optional[int] = None
#     fixed_point_days: Optional[int] = None
#     shipping_factory: Optional[str] = None
#     client_product_code: Optional[str] = None
#     purchasing_org: Optional[str] = None
#     item_group: Optional[str] = None
#     processing_type: Optional[str] = None
#     inventory_transfer_category: Optional[str] = None
#     created_at: Optional[str] = None
#     container_width: Optional[int] = None
#     container_depth: Optional[int] = None
#     container_height: Optional[int] = None
#     stackable: Optional[bool] = True
#     used_container_id: Optional[int] = None
#     can_advance: Optional[bool] = False
    
#     @classmethod
#     def from_dict(cls, data: dict):
#         """辞書からモデルを作成"""
#         valid_fields = {}
#         for field_name in cls.__annotations__.keys():
#             if field_name in data and data[field_name] is not None:
#                 if field_name in ['stackable', 'can_advance'] and isinstance(data[field_name], int):
#                     valid_fields[field_name] = bool(data[field_name])
#                 else:
#                     valid_fields[field_name] = data[field_name]
#         return cls(**valid_fields)
    
#     @classmethod
#     def from_orm(cls, orm_obj):
#         """SQLAlchemy ORMオブジェクトから変換"""
#         return cls(
#             id=orm_obj.id,
#             data_no=orm_obj.data_no,
#             factory=orm_obj.factory,
#             client_code=orm_obj.client_code,
#             calculation_date=orm_obj.calculation_date,
#             production_complete_date=orm_obj.production_complete_date,
#             modified_factory=orm_obj.modified_factory,
#             product_category=orm_obj.product_category,
#             product_code=orm_obj.product_code,
#             ac_code=orm_obj.ac_code,
#             processing_content=orm_obj.processing_content,
#             product_name=orm_obj.product_name,
#             delivery_location=orm_obj.delivery_location,
#             box_type=orm_obj.box_type,
#             capacity=orm_obj.capacity,
#             grouping_category=orm_obj.grouping_category,
#             form_category=orm_obj.form_category,
#             inspection_category=orm_obj.inspection_category,
#             ordering_category=orm_obj.ordering_category,
#             regular_replenishment_category=orm_obj.regular_replenishment_category,
#             lead_time=orm_obj.lead_time,
#             fixed_point_days=orm_obj.fixed_point_days,
#             shipping_factory=orm_obj.shipping_factory,
#             client_product_code=orm_obj.client_product_code,
#             purchasing_org=orm_obj.purchasing_org,
#             item_group=orm_obj.item_group,
#             processing_type=orm_obj.processing_type,
#             inventory_transfer_category=orm_obj.inventory_transfer_category,
#             created_at=str(orm_obj.created_at) if orm_obj.created_at else None,
#             container_width=orm_obj.container_width,
#             container_depth=orm_obj.container_depth,
#             container_height=orm_obj.container_height,
#             stackable=bool(orm_obj.stackable) if orm_obj.stackable is not None else True,
#             used_container_id=orm_obj.used_container_id,
#             can_advance=bool(orm_obj.can_advance) if hasattr(orm_obj, 'can_advance') and orm_obj.can_advance is not None else False
#         )


# # ProductionConstraint用のSQLAlchemy ORMモデル
# class ProductionConstraintORM(Base):
#     """生産制約モデル - SQLAlchemy ORM"""
#     __tablename__ = "production_constraints"
    
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     product_id = Column(Integer, nullable=False, unique=True)
#     daily_capacity = Column(Integer, nullable=False, default=1000)
#     smoothing_level = Column(Integer, nullable=False, default=70)  # decimal(5,2) → int
#     volume_per_unit = Column(Integer, nullable=False, default=100)  # decimal(10,2) → int
#     is_transport_constrained = Column(Boolean, nullable=False, default=False)
#     created_at = Column(TIMESTAMP)
#     updated_at = Column(TIMESTAMP)


# @dataclass
# class ProductConstraint:
#     """製品制約モデル - Dataclass"""
#     product_id: int
#     id: Optional[int] = None
#     daily_capacity: int = 1000
#     smoothing_level: float = 0.70
#     volume_per_unit: float = 1.00
#     is_transport_constrained: bool = False
#     created_at: Optional[str] = None
#     updated_at: Optional[str] = None
#     product_code: Optional[str] = None
#     product_name: Optional[str] = None
    
#     @classmethod
#     def from_dict(cls, data: dict):
#         """辞書からモデルを作成"""
#         valid_fields = {}
#         for field_name in cls.__annotations__.keys():
#             if field_name in data and data[field_name] is not None:
#                 if field_name == 'is_transport_constrained' and isinstance(data[field_name], int):
#                     valid_fields[field_name] = bool(data[field_name])
#                 else:
#                     valid_fields[field_name] = data[field_name]
#         return cls(**valid_fields)


# @dataclass
# class ProductContainerMapping:
#     """製品×容器紐付けモデル"""
#     product_id: int
#     container_id: int
#     id: Optional[int] = None
#     max_quantity: int = 100
#     is_primary: bool = False
#     created_at: Optional[str] = None
#     updated_at: Optional[str] = None
#     product_code: Optional[str] = None
#     product_name: Optional[str] = None
#     container_name: Optional[str] = None
    
#     @classmethod
#     def from_dict(cls, data: dict):
#         """辞書からモデルを作成"""
#         valid_fields = {}
#         for field_name in cls.__annotations__.keys():
#             if field_name in data and data[field_name] is not None:
#                 if field_name == 'is_primary' and isinstance(data[field_name], int):
#                     valid_fields[field_name] = bool(data[field_name])
#                 else:
#                     valid_fields[field_name] = data[field_name]
#         return cls(**valid_fields)


# app/domain/models/product.py
from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass
class Product:
    """製品モデル - 実際のproductsテーブル構造に完全対応"""
    id: int
    data_no: Optional[int] = None
    factory: Optional[str] = None
    client_code: Optional[int] = None
    calculation_date: Optional[date] = None
    production_complete_date: Optional[date] = None
    modified_factory: Optional[str] = None
    product_category: Optional[str] = None
    product_code: Optional[str] = None
    ac_code: Optional[str] = None
    processing_content: Optional[str] = None
    product_name: Optional[str] = None
    delivery_location: Optional[str] = None
    box_type: Optional[str] = None
    capacity: Optional[int] = None
    grouping_category: Optional[str] = None
    form_category: Optional[str] = None
    inspection_category: Optional[str] = None
    ordering_category: Optional[str] = None
    regular_replenishment_category: Optional[str] = None
    lead_time: Optional[int] = None
    fixed_point_days: Optional[int] = None
    shipping_factory: Optional[str] = None
    client_product_code: Optional[str] = None
    purchasing_org: Optional[str] = None
    item_group: Optional[str] = None
    processing_type: Optional[str] = None
    inventory_transfer_category: Optional[str] = None
    created_at: Optional[str] = None
    container_width: Optional[int] = None
    container_depth: Optional[int] = None
    container_height: Optional[int] = None
    stackable: Optional[bool] = True
    used_container_id: Optional[int] = None  # 使用容器ID
    used_truck_ids: Optional[str] = None  # 使用トラックID（カンマ区切り）
    can_advance: Optional[bool] = False  # 前倒し可能フラグ（追加予定）
    
    @classmethod
    def from_dict(cls, data: dict):
        """辞書からモデルを作成(余分なキーを無視)"""
        valid_fields = {}
        for field_name in cls.__annotations__.keys():
            if field_name in data and data[field_name] is not None:
                # tinyint(1)をboolに変換
                if field_name in ['stackable', 'can_advance'] and isinstance(data[field_name], int):
                    valid_fields[field_name] = bool(data[field_name])
                else:
                    valid_fields[field_name] = data[field_name]
        return cls(**valid_fields)


@dataclass
class ProductConstraint:
    """製品制約モデル - production_constraintsテーブル構造に完全対応"""
    product_id: int
    id: Optional[int] = None
    daily_capacity: int = 1000
    smoothing_level: float = 0.70
    volume_per_unit: float = 1.00
    is_transport_constrained: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # 結合用フィールド
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """辞書からモデルを作成"""
        valid_fields = {}
        for field_name in cls.__annotations__.keys():
            if field_name in data and data[field_name] is not None:
                # tinyint(1)をboolに変換
                if field_name == 'is_transport_constrained' and isinstance(data[field_name], int):
                    valid_fields[field_name] = bool(data[field_name])
                else:
                    valid_fields[field_name] = data[field_name]
        return cls(**valid_fields)


@dataclass
class ProductContainerMapping:
    """製品×容器紐付けモデル - product_container_mappingテーブル（新規作成予定）"""
    product_id: int
    container_id: int
    id: Optional[int] = None
    max_quantity: int = 100
    is_primary: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    # 結合用フィールド
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    container_name: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict):
        """辞書からモデルを作成"""
        valid_fields = {}
        for field_name in cls.__annotations__.keys():
            if field_name in data and data[field_name] is not None:
                if field_name == 'is_primary' and isinstance(data[field_name], int):
                    valid_fields[field_name] = bool(data[field_name])
                else:
                    valid_fields[field_name] = data[field_name]
        return cls(**valid_fields)