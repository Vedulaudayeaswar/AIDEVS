import React, { useRef } from "react";
import "./PreviewPanel.css";

const PreviewPanel = ({ html }) => {
  const iframeRef = useRef(null);

  const [nonce, setNonce] = React.useState(0);
  // Rendered via srcDoc in an opaque-origin sandbox (no allow-same-origin).
  const doc = React.useMemo(() => {
      const fullHTML =
        html ||
        `
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Preview</title>
          <style>
            body {
              margin: 0;
              padding: 40px;
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              min-height: 100vh;
              background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }
            .preview-placeholder {
              text-align: center;
              color: white;
            }
            .preview-placeholder h1 {
              font-size: 48px;
              margin-bottom: 16px;
              opacity: 0.9;
            }
            .preview-placeholder p {
              font-size: 18px;
              opacity: 0.7;
            }
            .preview-icon {
              font-size: 120px;
              margin-bottom: 24px;
            }
          </style>
        </head>
        <body>
          <div class="preview-placeholder">
            <div class="preview-icon">🎨</div>
            <h1>Live Preview</h1>
            <p>Your website will appear here as we build it together</p>
          </div>
        </body>
        </html>
      `;

      return fullHTML;
  }, [html]);

  return (
    <div className="preview-panel">
      <div className="preview-header">
        <div className="preview-title">
          <h3>Live Preview</h3>
          <span className="preview-status">
            {html ? "● Building" : "○ Waiting"}
          </span>
        </div>
        <div className="preview-controls">
          <button
            className="control-btn"
            onClick={() => {
              setNonce((n) => n + 1);
            }}
            title="Refresh Preview"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
          </button>
        </div>
      </div>
      <div className="iframe-container">
        <iframe
          ref={iframeRef}
          title="Website Preview"
          key={nonce}
          srcDoc={doc}
          sandbox="allow-scripts"
          className="preview-iframe"
        />
      </div>
    </div>
  );
};

export default PreviewPanel;
