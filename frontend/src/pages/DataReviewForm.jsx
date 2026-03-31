import React, { useEffect, useMemo, useState } from 'react';
import styles from './ChatbotOrchestrator.module.css';

function isEditableValue(value) {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value);
}

function toDisplayLabel(key) {
  return key
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

const GST_FIELD_ORDER = [
  'gstin',
  'legalName',
  'tradeName',
  'constitution',
  'dateOfLiability',
];

const GST_FIELD_ALIASES = {
  gst_in: 'gstin',
  gstin_number: 'gstin',
  legal_name: 'legalName',
  trade_name: 'tradeName',
  date_of_liability: 'dateOfLiability',
  constitution_of_business: 'constitution',
};

function normalizeEditableObject(source) {
  if (!source || typeof source !== 'object' || Array.isArray(source)) return {};
  return Object.entries(source).reduce((acc, [key, value]) => {
    if (!isEditableValue(value)) return acc;
    acc[key] = value == null ? '' : String(value);
    return acc;
  }, {});
}

function resolvePersonalData(extractedData) {
  if (!extractedData || typeof extractedData !== 'object' || Array.isArray(extractedData)) {
    return {};
  }

  const combinedData = extractedData?.validation?.combined_data ?? extractedData?.combined_data;
  if (combinedData && typeof combinedData === 'object' && !Array.isArray(combinedData)) {
    return normalizeEditableObject(combinedData);
  }

  const fallbackData = Object.entries(extractedData).reduce((acc, [key, value]) => {
    if (key === 'gst_data' || key === 'validation' || key === 'combined_data') return acc;
    if (!isEditableValue(value)) return acc;
    acc[key] = value;
    return acc;
  }, {});
  return normalizeEditableObject(fallbackData);
}

function resolveGstData(extractedData) {
  if (!extractedData || typeof extractedData !== 'object' || Array.isArray(extractedData)) {
    return { shouldRender: false, data: {} };
  }

  const gstPayload = extractedData?.gst_data ?? extractedData?.validation?.gst_data;
  if (
    !gstPayload
    || typeof gstPayload !== 'object'
    || Array.isArray(gstPayload)
    || Object.keys(gstPayload).length === 0
  ) {
    return { shouldRender: false, data: {} };
  }

  const normalizedGstData = normalizeEditableObject(gstPayload);
  const canonicalGstData = Object.entries(normalizedGstData).reduce((acc, [key, value]) => {
    const canonicalKey = GST_FIELD_ALIASES[key] ?? key;
    acc[canonicalKey] = value;
    return acc;
  }, {});

  const orderedGstData = GST_FIELD_ORDER.reduce((acc, key) => {
    acc[key] = canonicalGstData[key] ?? '';
    return acc;
  }, {});

  Object.entries(canonicalGstData).forEach(([key, value]) => {
    if (!(key in orderedGstData)) {
      orderedGstData[key] = value;
    }
  });

  return { shouldRender: true, data: orderedGstData };
}

export default function DataReviewForm({ agentMessage, extractedData, isSubmitting, onConfirm }) {
  const [personalFormData, setPersonalFormData] = useState({});
  const [gstFormData, setGstFormData] = useState({});
  const [showGstSection, setShowGstSection] = useState(false);

  useEffect(() => {
    setPersonalFormData(resolvePersonalData(extractedData));
    const gstState = resolveGstData(extractedData);
    setGstFormData(gstState.data);
    setShowGstSection(gstState.shouldRender);
  }, [extractedData]);

  const handlePersonalFieldChange = (event) => {
    const { name, value } = event.target;
    setPersonalFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleGstFieldChange = (event) => {
    const { name, value } = event.target;
    setGstFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    const finalData = {
      ...personalFormData,
      ...(showGstSection ? { gst_data: gstFormData } : {}),
    };
    if (typeof onConfirm === 'function') {
      onConfirm(finalData);
    }
  };

  const personalFields = useMemo(() => Object.keys(personalFormData), [personalFormData]);
  const gstFields = useMemo(() => Object.keys(gstFormData), [gstFormData]);
  const totalFieldCount = personalFields.length + (showGstSection ? gstFields.length : 0);

  return (
    <div className={styles.viewCard}>
      <h2 className={styles.viewTitle}>Review Extracted Data</h2>
      <p className={styles.agentMessage}>
        {agentMessage || 'Please review and correct extracted KYC details before submission.'}
      </p>

      <form className={styles.reviewForm} onSubmit={handleSubmit}>
        {totalFieldCount === 0 && (
          <p className={styles.metaText}>No extracted fields were returned by the backend.</p>
        )}

        {personalFields.length > 0 && (
          <div className={styles.reviewSection}>
            <h3 className={styles.reviewSectionTitle}>Personal Information</h3>
            <div className={styles.reviewGrid}>
              {personalFields.map((field) => (
                <div key={field} className={styles.reviewField}>
                  <label className={styles.label} htmlFor={`review-${field}`}>
                    {toDisplayLabel(field)}
                  </label>
                  <input
                    id={`review-${field}`}
                    type="text"
                    name={field}
                    value={personalFormData[field] ?? ''}
                    onChange={handlePersonalFieldChange}
                    className={styles.input}
                    disabled={isSubmitting}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {showGstSection && (
          <div className={styles.reviewSection}>
            <h3 className={styles.reviewSectionTitle}>Business Information</h3>
            <div className={styles.reviewGrid}>
              {gstFields.map((field) => (
                <div key={field} className={styles.reviewField}>
                  <label className={styles.label} htmlFor={`review-gst-${field}`}>
                    {toDisplayLabel(field)}
                  </label>
                  <input
                    id={`review-gst-${field}`}
                    type="text"
                    name={field}
                    value={gstFormData[field] ?? ''}
                    onChange={handleGstFieldChange}
                    className={styles.input}
                    disabled={isSubmitting}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <button className={styles.primaryBtn} type="submit" disabled={isSubmitting || totalFieldCount === 0}>
          {isSubmitting ? 'Submitting...' : 'Confirm & Submit'}
        </button>
      </form>
    </div>
  );
}
