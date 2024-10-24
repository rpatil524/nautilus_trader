// -------------------------------------------------------------------------------------------------
//  Copyright (C) 2015-2024 Nautech Systems Pty Ltd. All rights reserved.
//  https://nautechsystems.io
//
//  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
//  You may not use this file except in compliance with the License.
//  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
//
//  Unless required by applicable law or agreed to in writing, software
//  distributed under the License is distributed on an "AS IS" BASIS,
//  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//  See the License for the specific language governing permissions and
//  limitations under the License.
// -------------------------------------------------------------------------------------------------

use std::env;

use nautilus_common::version::USER_AGENT;

use super::{
    types::{InstrumentInfo, Response},
    TARDIS_BASE_URL,
};
use crate::tardis::enums::Exchange;

pub type Result<T> = std::result::Result<T, Error>;

/// HTTP errors for the Tardis HTTP client.
#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// An error when sending a request to the server.
    #[error("Error sending request: {0}")]
    Request(#[from] reqwest::Error),

    /// An error when deserializing the response from the server.
    #[error("Error deserializing message: {0}")]
    Deserialization(#[from] serde_json::Error),
}

/// A Tardis HTTP API client.
/// See <https://docs.tardis.dev/api/http>.
#[cfg_attr(
    feature = "python",
    pyo3::pyclass(module = "nautilus_trader.core.nautilus_pyo3.adapters")
)]
pub struct TardisHttpClient {
    base_url: String,
    api_key: String,
    client: reqwest::Client,
}

impl TardisHttpClient {
    /// Creates a new [`TardisHttpClient`] instance.
    pub fn new(api_key: Option<&str>, base_url: Option<&str>) -> Self {
        let api_key = api_key.map(ToString::to_string).unwrap_or_else(|| {
            env::var("TARDIS_API_KEY").expect(
                "API key must be provided or set in the 'TARDIS_API_KEY' environment variable",
            )
        });

        Self {
            base_url: base_url.unwrap_or(TARDIS_BASE_URL).to_string(),
            api_key,
            client: reqwest::Client::builder()
                .user_agent(USER_AGENT.clone())
                .build()
                .unwrap(),
        }
    }

    /// Returns all instrument definitions for the given `exchange`.
    /// See <https://docs.tardis.dev/api/instruments-metadata-api>
    pub async fn instruments(&self, exchange: Exchange) -> Result<Response<Vec<InstrumentInfo>>> {
        Ok(self
            .client
            .get(format!("{}/instruments/{exchange}", &self.base_url))
            .bearer_auth(&self.api_key)
            .send()
            .await?
            .json::<Response<Vec<InstrumentInfo>>>()
            .await?)
    }

    /// Returns the instrument definition for a given `exchange` and `symbol`.
    /// See <https://docs.tardis.dev/api/instruments-metadata-api#single-instrument-info-endpoint>
    pub async fn instrument(
        &self,
        exchange: Exchange,
        symbol: String,
    ) -> Result<Response<InstrumentInfo>> {
        Ok(self
            .client
            .get(format!(
                "{}/instruments/{exchange}/{symbol}",
                &self.base_url
            ))
            .bearer_auth(&self.api_key)
            .send()
            .await?
            .json::<Response<InstrumentInfo>>()
            .await?)
    }
}
