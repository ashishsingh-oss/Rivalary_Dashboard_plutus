exports.handler = async function handler() {
  const revenueUrl = process.env.REVENUE_CSV_URL;
  const vcUrl = process.env.VC_CSV_URL;

  if (!revenueUrl || !vcUrl) {
    return {
      statusCode: 500,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify({
        error: "missing_env",
        message: "Set REVENUE_CSV_URL and VC_CSV_URL in Netlify environment variables.",
      }),
    };
  }

  const fetchCsv = async (url) => {
    const sep = url.includes("?") ? "&" : "?";
    const res = await fetch(`${url}${sep}_t=${Date.now()}`, {
      headers: {
        Accept: "text/csv,text/plain,*/*",
      },
    });
    if (!res.ok) {
      throw new Error(`Upstream fetch failed (${res.status}) for ${url}`);
    }
    return res.text();
  };

  try {
    const [revenueCsv, vcCsv] = await Promise.all([fetchCsv(revenueUrl), fetchCsv(vcUrl)]);
    return {
      statusCode: 200,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "cache-control": "no-store",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify({
        revenueCsv,
        vcCsv,
        sources: {
          revenue: revenueUrl,
          vc: vcUrl,
        },
      }),
    };
  } catch (err) {
    return {
      statusCode: 502,
      headers: {
        "content-type": "application/json; charset=utf-8",
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify({
        error: "upstream_fetch_failed",
        message: String(err && err.message ? err.message : err),
      }),
    };
  }
};

