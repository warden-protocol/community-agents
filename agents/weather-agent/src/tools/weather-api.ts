import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';
import { Logger } from '../common';

const logger = new Logger('WeatherAPI');

// WeatherAPI base URL
const WEATHER_API_BASE_URL = 'https://api.weatherapi.com/v1';

// Types for WeatherAPI responses
interface WeatherCondition {
  text: string;
  icon: string;
  code: number;
}

interface CurrentWeather {
  temp_c: number;
  temp_f: number;
  condition: WeatherCondition;
  wind_mph: number;
  wind_kph: number;
  wind_dir: string;
  pressure_mb: number;
  pressure_in: number;
  precip_mm: number;
  precip_in: number;
  humidity: number;
  cloud: number;
  feelslike_c: number;
  feelslike_f: number;
  vis_km: number;
  vis_miles: number;
  uv: number;
  gust_mph: number;
  gust_kph: number;
}

interface Location {
  name: string;
  region: string;
  country: string;
  lat: number;
  lon: number;
  tz_id: string;
  localtime: string;
}

interface ForecastDay {
  date: string;
  day: {
    maxtemp_c: number;
    maxtemp_f: number;
    mintemp_c: number;
    mintemp_f: number;
    avgtemp_c: number;
    avgtemp_f: number;
    maxwind_mph: number;
    maxwind_kph: number;
    totalprecip_mm: number;
    totalprecip_in: number;
    avgvis_km: number;
    avgvis_miles: number;
    avghumidity: number;
    condition: WeatherCondition;
    uv: number;
  };
  astro: {
    sunrise: string;
    sunset: string;
    moonrise: string;
    moonset: string;
    moon_phase: string;
  };
  hour: Array<{
    time: string;
    temp_c: number;
    temp_f: number;
    condition: WeatherCondition;
    wind_mph: number;
    wind_kph: number;
    wind_dir: string;
    pressure_mb: number;
    pressure_in: number;
    precip_mm: number;
    precip_in: number;
    humidity: number;
    cloud: number;
    feelslike_c: number;
    feelslike_f: number;
    windchill_c: number;
    windchill_f: number;
    heatindex_c: number;
    heatindex_f: number;
    dewpoint_c: number;
    dewpoint_f: number;
    will_it_rain: number;
    chance_of_rain: number;
    will_it_snow: number;
    chance_of_snow: number;
    vis_km: number;
    vis_miles: number;
    gust_mph: number;
    gust_kph: number;
    uv: number;
  }>;
}

interface CurrentWeatherResponse {
  location: Location;
  current: CurrentWeather;
}

interface ForecastWeatherResponse {
  location: Location;
  current: CurrentWeather;
  forecast: {
    forecastday: ForecastDay[];
  };
}

/**
 * Fetches current weather for a location from WeatherAPI
 */
async function getCurrentWeather(
  location: string,
  apiKey: string,
): Promise<string> {
  logger.info(`Fetching current weather for: ${location}`);

  const url = `${WEATHER_API_BASE_URL}/current.json?key=${apiKey}&q=${encodeURIComponent(location)}&aqi=no`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        `WeatherAPI error: ${error.error?.message || response.statusText}`,
      );
    }

    const data: CurrentWeatherResponse = await response.json();

    const result = {
      location: {
        name: data.location.name,
        region: data.location.region,
        country: data.location.country,
        localtime: data.location.localtime,
      },
      current: {
        temp_c: data.current.temp_c,
        temp_f: data.current.temp_f,
        condition: data.current.condition.text,
        wind_kph: data.current.wind_kph,
        wind_dir: data.current.wind_dir,
        humidity: data.current.humidity,
        cloud: data.current.cloud,
        feelslike_c: data.current.feelslike_c,
        feelslike_f: data.current.feelslike_f,
        uv: data.current.uv,
      },
    };

    return JSON.stringify(result, null, 2);
  } catch (error) {
    logger.error('Error fetching current weather:', error);
    throw error;
  }
}

/**
 * Fetches weather forecast for a location from WeatherAPI
 */
async function getForecastWeather(
  location: string,
  days: number,
  apiKey: string,
): Promise<string> {
  logger.info(`Fetching ${days}-day forecast for: ${location}`);

  // WeatherAPI allows up to 14 days forecast
  const forecastDays = Math.min(Math.max(days, 1), 14);

  const url = `${WEATHER_API_BASE_URL}/forecast.json?key=${apiKey}&q=${encodeURIComponent(location)}&days=${forecastDays}&aqi=no&alerts=no`;

  try {
    const response = await fetch(url);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(
        `WeatherAPI error: ${error.error?.message || response.statusText}`,
      );
    }

    const data: ForecastWeatherResponse = await response.json();

    const result = {
      location: {
        name: data.location.name,
        region: data.location.region,
        country: data.location.country,
        localtime: data.location.localtime,
      },
      current: {
        temp_c: data.current.temp_c,
        temp_f: data.current.temp_f,
        condition: data.current.condition.text,
        humidity: data.current.humidity,
      },
      forecast: data.forecast.forecastday.map((day) => ({
        date: day.date,
        maxtemp_c: day.day.maxtemp_c,
        mintemp_c: day.day.mintemp_c,
        avgtemp_c: day.day.avgtemp_c,
        maxtemp_f: day.day.maxtemp_f,
        mintemp_f: day.day.mintemp_f,
        avgtemp_f: day.day.avgtemp_f,
        condition: day.day.condition.text,
        maxwind_kph: day.day.maxwind_kph,
        totalprecip_mm: day.day.totalprecip_mm,
        avghumidity: day.day.avghumidity,
        uv: day.day.uv,
        sunrise: day.astro.sunrise,
        sunset: day.astro.sunset,
      })),
    };

    logger.info(
      `Successfully fetched ${forecastDays}-day forecast for ${data.location.name}`,
    );
    return JSON.stringify(result, null, 2);
  } catch (error) {
    logger.error('Error fetching weather forecast:', error);
    throw error;
  }
}

/**
 * Creates LangChain tools for WeatherAPI
 */
export function createWeatherTools(apiKey: string): DynamicStructuredTool[] {
  if (!apiKey) {
    throw new Error('WEATHER_API_KEY is required');
  }

  const currentWeatherTool = new DynamicStructuredTool({
    name: 'get_current_weather',
    description:
      'Get current weather conditions for a specific location. Use this tool to fetch real-time weather information including temperature, humidity, wind, and conditions. Location can be city name, US zipcode, UK postcode, Canada postal code, IP address, or lat/lon coordinates.',
    schema: z.object({
      location: z
        .string()
        .describe(
          'Location to get weather for (e.g., "London", "New York", "48.8567,2.3508")',
        ),
    }),
    func: async ({ location }): Promise<string> => {
      return await getCurrentWeather(location, apiKey);
    },
  });

  const forecastWeatherTool = new DynamicStructuredTool({
    name: 'get_weather_forecast',
    description:
      'Get weather forecast for a specific location for up to 14 days. Use this tool to fetch future weather predictions including daily min/max temperatures, conditions, precipitation, and astronomical data. Location can be city name, US zipcode, UK postcode, Canada postal code, IP address, or lat/lon coordinates.',
    schema: z.object({
      location: z
        .string()
        .describe(
          'Location to get forecast for (e.g., "London", "New York", "48.8567,2.3508")',
        ),
      days: z
        .number()
        .min(1)
        .max(14)
        .default(3)
        .describe(
          'Number of days to forecast (1-14, default: 3). Free API key supports up to 3 days.',
        ),
    }),
    func: async ({ location, days }): Promise<string> => {
      return await getForecastWeather(location, days, apiKey);
    },
  });

  return [currentWeatherTool, forecastWeatherTool];
}
