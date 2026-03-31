import React, { useState } from 'react';
import styles from './ChatbotOrchestrator.module.css';

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(0)) + ' ' + sizes[i];
};

const getFileExtension = (filename) => {
  return filename?.split('.').pop().toUpperCase() || '';
};

export default function KycUploadView({ agentMessage, dataRequired, isSubmitting, onUploadDocuments }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragActive, setIsDragActive] = useState(false);

  const handleFiles = (files) => {
    if (!files || files.length === 0) return;
    const newFiles = Array.from(files).map((file) => ({
      file,
      id: `${file.name}_${file.size}_${Date.now()}_${Math.random()}`,
      progress: 0,
      status: 'default',
      error: ''
    }));
    setSelectedFiles((prev) => [...prev, ...newFiles]);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setIsDragActive(true);
  };

  const onDragLeave = (e) => {
    e.preventDefault();
    setIsDragActive(false);
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
      e.dataTransfer.clearData();
    }
  };

  const handleRemoveFile = (id) => {
    setSelectedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (selectedFiles.length === 0 || typeof onUploadDocuments !== 'function') return;

    setIsUploading(true);

    // Simulate progress
    for (let i = 0; i <= 90; i += 15) {
      setSelectedFiles((prev) =>
        prev.map((f) => (f.status !== 'complete' ? { ...f, status: 'uploading', progress: i } : f))
      );
      await new Promise((resolve) => setTimeout(resolve, 150));
    }

    try {
      const filesToUpload = selectedFiles.map((f) => f.file);
      await onUploadDocuments(filesToUpload);
      setSelectedFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'complete', progress: 100, error: '' }))
      );
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Document upload failed. Try again.';
      setSelectedFiles((prev) =>
        prev.map((f) => (f.status !== 'complete' ? { ...f, status: 'failed', error: message } : f))
      );
    } finally {
      setIsUploading(false);
    }
  };

  const getCardClass = (status) => {
    if (status === 'failed') return `${styles.fileCard} ${styles.fileCardFailed}`;
    return styles.fileCard;
  };

  return (
    <div className={styles.viewCard}>
      <h2 className={styles.viewTitle}>KYC Document Upload</h2>
      <p className={styles.agentMessage}>{agentMessage || 'Upload Aadhaar / PAN documents.'}</p>
      {dataRequired?.length > 0 && <p className={styles.metaText}>Required: {dataRequired.join(', ')}</p>}

      <form className={styles.form} style={{ maxWidth: '100%' }} onSubmit={handleSubmit}>
        <div
          className={`${styles.enhancedUploadZone} ${isDragActive ? styles.dragActive : ''}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <div className={styles.uploadIconWrap}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </div>
          <div className={styles.uploadTextWrap}>
            <span className={styles.uploadLinkText}>Click to upload</span>
            <span className={styles.uploadNormalText}> or drag and drop</span>
          </div>
          <p className={styles.uploadHintText}>SVG, PNG, JPG or GIF (max. 800x400px)</p>
          <input
            id="kyc-files"
            type="file"
            multiple
            accept=".pdf,.jpg,.jpeg,.png,.svg,.gif"
            onChange={(event) => {
              handleFiles(event.target.files);
              event.target.value = ''; // Reset to allow re-upload same file
            }}
            className={styles.hiddenInput}
            disabled={isSubmitting || isUploading}
          />
          <label htmlFor="kyc-files" className={styles.uploadZoneOverlay}></label>
        </div>

        {selectedFiles.length > 0 && (
          <div className={styles.enhancedFileList}>
            {selectedFiles.map((f) => (
              <div key={f.id} className={getCardClass(f.status)}>
                <div className={styles.fileBadgeWrap}>
                  <div className={`${styles.fileBadge} ${styles['badge' + getFileExtension(f.file.name)] || styles.badgeDefault}`}>
                    {getFileExtension(f.file.name).substring(0, 4)}
                  </div>
                </div>
                <div className={styles.fileCardContent}>
                  <div className={styles.fileHeader}>
                    <div className={styles.fileInfoText}>
                      <span className={styles.fileName}>{f.file.name}</span>
                      <span className={styles.fileMeta}>
                        {formatSize(f.file.size)}
                        {f.status === 'uploading' && (
                          <span className={styles.uploadingText}>
                            {' '}
                            |{' '}
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={styles.spinIcon}>
                              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                            </svg>{' '}
                            Uploading...
                          </span>
                        )}
                        {f.status === 'complete' && (
                          <span className={styles.completeText}>
                            {' '}
                            |{' '}
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                              <polyline points="22 4 12 14.01 9 11.01"></polyline>
                            </svg>{' '}
                            Complete
                          </span>
                        )}
                        {f.status === 'failed' && (
                          <span className={styles.failedText}>
                            {' '}
                            |{' '}
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <circle cx="12" cy="12" r="10" />
                              <line x1="15" y1="9" x2="9" y2="15" />
                              <line x1="9" y1="9" x2="15" y2="15" />
                            </svg>{' '}
                            Failed
                          </span>
                        )}
                      </span>
                    </div>
                    <button
                      type="button"
                      className={styles.deleteBtn}
                      onClick={() => handleRemoveFile(f.id)}
                      disabled={isSubmitting || isUploading}
                    >
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>

                  {f.status !== 'failed' && (
                    <div className={styles.progressTrack}>
                      <div
                        className={`${styles.progressBar} ${f.status === 'complete' ? styles.progressComplete : ''}`}
                        style={{ width: `${f.progress}%` }}
                      ></div>
                    </div>
                  )}

                  {f.status === 'failed' && (
                    <div className={styles.errorSection}>
                      <button
                        type="button"
                        className={styles.tryAgainBtn}
                        onClick={() => {
                          setSelectedFiles((prev) =>
                            prev.map((item) =>
                              item.id === f.id ? { ...item, status: 'default', error: '', progress: 0 } : item
                            )
                          );
                        }}
                      >
                        Try again
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <button className={styles.primaryBtn} type="submit" disabled={isSubmitting || isUploading || selectedFiles.length === 0} style={{ marginTop: '4px', alignSelf: 'center' }}>
          {isUploading || isSubmitting ? 'Submitting...' : 'Submit Upload'}
        </button>
      </form>
    </div>
  );
}
