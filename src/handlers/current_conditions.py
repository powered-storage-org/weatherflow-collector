# current_conditions.py

"""
Current Conditions Handler for WeatherFlow Collector

This handler stores real-time current weather conditions in a dedicated measurement.
It processes live observation data (not forecasts) and stores it in 'weatherflow_current_conditions'.

Key Features:
- Stores only current/live weather data (not forecast data)
- Includes all metrics needed for Grafana alerts
- Matches the metrics used in the provided alert configuration
- Updates frequently with the latest conditions

Metrics Stored:
- Temperature metrics: air_temperature, calculated_heat_index, calculated_wind_chill
- Humidity metrics: relative_humidity, calculated_vpd, calculated_absolute_humidity
- Wind metrics: wind_avg, wind_gust, wind_lull, wind_direction, calculated_beaufort_scale_rating
- Precipitation metrics: rain_accumulated, precipitation_type, precip_total_1h, local_daily_rain_accumulation
- Lightning metrics: lightning_strike_count, lightning_strike_avg_distance
- Pressure metrics: station_pressure, calculated_sea_level_pressure, pressure_trend
- Solar metrics: uv, solar_radiation, illuminance
- System metrics: battery, report_interval
"""

import time
import logger
import utils.utils as utils
from utils.calculate_weather_metrics import CalculateWeatherMetrics

logger_CurrentConditionsHandler = logger.get_module_logger(__name__ + ".CurrentConditionsHandler")


class CurrentConditionsHandler:
    def __init__(self, event_manager):
        self.event_manager = event_manager
        self.collector_type = "current_conditions"
        logger_CurrentConditionsHandler.info("CurrentConditionsHandler initialized")

    async def process_data(self, full_data):
        """
        Process incoming weather observation data and store current conditions.
        
        This handler only processes real-time observation data, not forecasts.
        It extracts all relevant metrics and stores them in weatherflow_current_conditions.
        """
        try:
            metadata = full_data.get("metadata", {})
            collector_type = metadata.get("collector_type", "")
            
            # Only process real observation data, not forecasts
            if "forecast" in collector_type:
                logger_CurrentConditionsHandler.debug("Skipping forecast data")
                return
            
            # Skip if no station info (can't tag properly)
            station_info = full_data.get("station_info", {})
            if not station_info:
                logger_CurrentConditionsHandler.debug("No station_info available, skipping")
                return
            
            data = full_data.get("data", {})
            
            # Extract observation data
            # Check if this is from obs_st, obs_air, or REST API
            if "obs" in data and isinstance(data["obs"], list) and len(data["obs"]) > 0:
                # UDP/WebSocket observation data
                obs_data = data["obs"][0]
                fields = self._extract_obs_fields(obs_data, collector_type)
            else:
                # REST API observation data (already in field format)
                # Filter out non-scalar fields (lists, dicts, etc.)
                fields = {}
                for k, v in data.items():
                    if k not in ["type", "hub_sn", "serial_number", "device_id", "obs", "ob"]:
                        # Only include scalar values (numbers, strings, booleans)
                        if isinstance(v, (int, float, str, bool)) or v is None:
                            fields[k] = v
            
            # Normalize fields
            fields = utils.normalize_fields(fields)
            
            # Remove any remaining list or dict fields after normalization
            fields = {k: v for k, v in fields.items() 
                     if isinstance(v, (int, float, str, bool)) or v is None}
            
            # Skip if no useful fields
            if not fields or len(fields) == 0:
                logger_CurrentConditionsHandler.debug("No valid fields to store, skipping")
                return
            
            # Calculate additional weather metrics (only if we have the required data)
            if fields.get("air_temperature") is not None and fields.get("relative_humidity") is not None:
                weather_data = {
                    "air_temperature": fields.get("air_temperature"),
                    "relative_humidity": fields.get("relative_humidity"),
                    "station_pressure": fields.get("station_pressure"),
                    "wind_avg": fields.get("wind_avg"),
                    "elevation": station_info.get("station_elevation", 0)
                }
                
                try:
                    additional_metrics = CalculateWeatherMetrics.calculate_weather_metrics(weather_data)
                    # Only add valid scalar metrics
                    for k, v in additional_metrics.items():
                        if isinstance(v, (int, float, str, bool)) or v is None:
                            fields[k] = v
                except Exception as e:
                    logger_CurrentConditionsHandler.warning(f"Error calculating weather metrics: {e}")
            
            # Create tags - ensure all tag values are strings
            tags = {
                "collector_type": str(collector_type),
                "station_id": str(station_info.get("station_id", metadata.get("station_id", "unknown"))),
            }
            
            # Add station information as tags (convert all to strings)
            for key in ["station_name", "station_latitude", "station_longitude", 
                       "station_elevation", "station_time_zone"]:
                if key in station_info and station_info[key] is not None:
                    tags[key] = str(station_info[key])
            
            # Get timestamp
            timestamp = fields.pop("timestamp", None)  # Remove from fields
            if timestamp is None:
                timestamp = int(time.time())
            else:
                timestamp = int(timestamp)
            
            # Final validation - ensure no None values in fields
            fields = {k: v for k, v in fields.items() if v is not None}
            
            # Skip if no fields left after filtering
            if not fields:
                logger_CurrentConditionsHandler.debug("No valid fields after filtering None values, skipping")
                return
            
            # Prepare data for InfluxDB
            measurement = "weatherflow_current_conditions"
            
            collector_data_with_meta = {
                "data_type": "single",
                "measurement": measurement,
                "tags": tags,
                "fields": fields,
                "timestamp": timestamp,
            }
            
            # Publish to InfluxDB
            await self.event_manager.publish(
                "influxdb_storage_event",
                collector_data_with_meta
            )
            
            logger_CurrentConditionsHandler.debug(
                f"Published {len(fields)} fields to weatherflow_current_conditions for station {tags.get('station_id')}"
            )
            
        except Exception as e:
            logger_CurrentConditionsHandler.error(f"Error processing current conditions data: {e}")
    
    def _extract_obs_fields(self, obs_data, collector_type):
        """
        Extract fields from observation array based on collector type.
        """
        fields = {}
        
        if "obs_st" in collector_type or isinstance(obs_data, list) and len(obs_data) >= 18:
            # Tempest obs_st format
            field_mapping = {
                "timestamp": 0,
                "wind_lull": 1,
                "wind_avg": 2,
                "wind_gust": 3,
                "wind_direction": 4,
                "wind_sample_interval": 5,
                "station_pressure": 6,
                "air_temperature": 7,
                "relative_humidity": 8,
                "illuminance": 9,
                "uv": 10,
                "solar_radiation": 11,
                "rain_accumulated": 12,
                "precipitation_type": 13,
                "lightning_strike_avg_distance": 14,
                "lightning_strike_count": 15,
                "battery": 16,
                "report_interval": 17,
            }
            
            for field_name, position in field_mapping.items():
                if position < len(obs_data):
                    fields[field_name] = obs_data[position]
        
        elif "obs_air" in collector_type:
            # Air obs format
            field_mapping = {
                "timestamp": 0,
                "station_pressure": 1,
                "air_temperature": 2,
                "relative_humidity": 3,
                "lightning_strike_count": 4,
                "lightning_strike_avg_distance": 5,
                "battery": 6,
                "report_interval": 7,
            }
            
            for field_name, position in field_mapping.items():
                if position < len(obs_data):
                    fields[field_name] = obs_data[position]
        
        elif "obs_sky" in collector_type:
            # Sky obs format
            field_mapping = {
                "timestamp": 0,
                "illuminance": 1,
                "uv": 2,
                "rain_accumulated": 3,
                "wind_lull": 4,
                "wind_avg": 5,
                "wind_gust": 6,
                "wind_direction": 7,
                "battery": 8,
                "report_interval": 9,
                "solar_radiation": 10,
                "local_daily_rain_accumulation": 11,
                "precipitation_type": 12,
            }
            
            for field_name, position in field_mapping.items():
                if position < len(obs_data):
                    fields[field_name] = obs_data[position]
        
        return fields
    
    async def update(self, full_data):
        """
        Update method called by event manager.
        """
        await self.process_data(full_data)
