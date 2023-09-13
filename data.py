import geopandas as gpd
import pandas as pd

df_requests = pd.read_parquet("./data/shipping_data.parquet")
gdf_ports = gpd.read_parquet("./data/ports_data.parquet")
gdf_ports["coords"] = gdf_ports.geometry.apply(lambda x: [x.x, x.y])
