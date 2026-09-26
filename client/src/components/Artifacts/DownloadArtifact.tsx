import React, { useState } from 'react';
import { Download, CircleCheckBig } from 'lucide-react';
import type { Artifact } from '~/common';
import { Button } from '@librechat/client';
import useArtifactProps from '~/hooks/Artifacts/useArtifactProps';
import { useCodeState } from '~/Providers/EditorContext';
import { pdfArtifactUrl } from '~/utils/artifacts';
import { useLocalize } from '~/hooks';

const DownloadArtifact = ({ artifact }: { artifact: Artifact }) => {
  const localize = useLocalize();
  const { currentCode } = useCodeState();
  const [isDownloaded, setIsDownloaded] = useState(false);
  const { fileKey: fileName } = useArtifactProps({ artifact });

  const handleDownload = () => {
    try {
      const content = currentCode ?? artifact.content ?? '';
      if (!content) {
        return;
      }
      /* the PDF report downloads the file itself, not the path stored as artifact content */
      const pdfUrl = pdfArtifactUrl(artifact);
      const url = pdfUrl ?? window.URL.createObjectURL(new Blob([content], { type: 'text/plain' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = (pdfUrl != null ? artifact.title : undefined) ?? fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      if (pdfUrl == null) {
        window.URL.revokeObjectURL(url);
      }
      setIsDownloaded(true);
      setTimeout(() => setIsDownloaded(false), 3000);
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  return (
    <Button
      size="icon"
      variant="ghost"
      className="h-9 w-9"
      onClick={handleDownload}
      aria-label={localize('com_ui_download_artifact')}
    >
      {isDownloaded ? (
        <CircleCheckBig size={16} aria-hidden="true" />
      ) : (
        <Download size={16} aria-hidden="true" />
      )}
    </Button>
  );
};

export default DownloadArtifact;
