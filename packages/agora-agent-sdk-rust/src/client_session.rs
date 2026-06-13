//! Session and artifact API methods for AgoraClient.

use crate::client::AgoraClient;
use crate::error::Result;
use crate::session::{SessionFilter, SessionRecord};

impl AgoraClient {
    /// Query session records.
    pub async fn query_sessions(&self, filter: &SessionFilter) -> Result<Vec<SessionRecord>> {
        let url = format!("{}/api/v1/sessions", self.http_base());
        let resp = self.http.get(&url).query(filter).send().await?;
        let records: Vec<SessionRecord> = resp.json().await?;
        Ok(records)
    }

    /// Retrieve a project artifact.
    pub async fn get_artifact(&self, project_id: &str, key: &str) -> Result<Vec<u8>> {
        let url = format!(
            "{}/api/v1/projects/{}/artifacts/{}",
            self.http_base(),
            project_id,
            key
        );
        let resp = self.http.get(&url).send().await?;
        let bytes = resp.bytes().await?;
        Ok(bytes.to_vec())
    }

    /// Store a project artifact.
    pub async fn put_artifact(&self, project_id: &str, key: &str, value: &[u8]) -> Result<()> {
        let url = format!(
            "{}/api/v1/projects/{}/artifacts/{}",
            self.http_base(),
            project_id,
            key
        );
        self.http.put(&url).body(value.to_vec()).send().await?;
        Ok(())
    }

    /// Helper: convert ws:// URL to http:// base.
    pub fn http_base(&self) -> String {
        self.config
            .coordinator_url
            .replace("ws://", "http://")
            .replace("wss://", "https://")
    }
}
