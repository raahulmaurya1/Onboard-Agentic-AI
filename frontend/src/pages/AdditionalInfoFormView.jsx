import React, { useEffect, useMemo, useState } from 'react';
import styles from './ChatbotOrchestrator.module.css';

const SCALAR_TYPES = new Set(['text', 'number', 'date', 'dropdown', 'radio', 'boolean', 'select']);
const ARRAY_TYPES = new Set(['array', 'list', 'repeatable']);
const PAN_PATTERN = /^[A-Z]{5}[0-9]{4}[A-Z]$/;
const DEFAULT_SME_PARTNER_FIELDS = [
  {
    key: 'name',
    label: 'Name',
    type: 'text',
    required: true,
    options: [],
    placeholder: 'Enter full name',
    isPanField: false,
  },
  {
    key: 'pan',
    label: 'PAN',
    type: 'text',
    required: true,
    options: [],
    placeholder: 'ABCDE1234F',
    isPanField: true,
  },
  {
    key: 'role',
    label: 'Role',
    type: 'dropdown',
    required: true,
    options: ['Partner', 'Director', 'Authorized Signatory'].map(normalizeOption),
    placeholder: '',
    isPanField: false,
  },
];

function isObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function slugify(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function toLabel(value) {
  return String(value || '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getPath(parentPath, key) {
  const cleanKey = String(key || '').trim();
  if (!cleanKey) return parentPath;
  if (!parentPath) return cleanKey;
  if (cleanKey.includes('.')) return cleanKey;
  return `${parentPath}.${cleanKey}`;
}

function normalizeOption(option, index) {
  if (typeof option === 'string' || typeof option === 'number' || typeof option === 'boolean') {
    const value = String(option);
    return { label: value, value };
  }
  if (isObject(option)) {
    const value = String(option.value ?? option.id ?? option.key ?? index + 1);
    const label = String(option.label ?? option.name ?? option.title ?? value);
    return { label, value };
  }
  return { label: `Option ${index + 1}`, value: String(index + 1) };
}

function normalizeCondition(value) {
  if (!value) return null;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parts = trimmed.split('=');
    if (parts.length === 2) return { field: parts[0].trim(), equals: parts[1].trim() };
    return { field: trimmed, equals: 'Yes' };
  }
  if (isObject(value)) {
    const field = String(value.field ?? value.key ?? value.name ?? '').trim();
    if (!field) return null;
    const equals =
      value.equals != null
        ? String(value.equals)
        : value.value != null
          ? String(value.value)
          : 'Yes';
    return {
      field,
      equals,
      truthy: Boolean(value.truthy),
    };
  }
  return null;
}

function isTruthyValue(value) {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (['', 'no', 'false', '0'].includes(normalized)) return false;
  if (['yes', 'true', '1'].includes(normalized)) return true;
  return Boolean(value);
}

function resolveValueByKey(values, key) {
  const target = String(key || '').trim().toLowerCase();
  if (!target) return undefined;

  const keys = Object.keys(values);
  const exact = keys.find((entry) => entry.toLowerCase() === target);
  if (exact) return values[exact];

  const tail = keys.find((entry) => entry.split('.').slice(-1)[0].toLowerCase() === target);
  if (tail) return values[tail];

  const slugTarget = slugify(target);
  const slugMatch = keys.find((entry) => slugify(entry) === slugTarget);
  return slugMatch ? values[slugMatch] : undefined;
}

function evaluateCondition(condition, values) {
  if (!condition) return true;
  const dependent = resolveValueByKey(values, condition.field);
  if (typeof condition.equals === 'string') {
    return String(dependent ?? '').trim().toLowerCase() === condition.equals.trim().toLowerCase();
  }
  if (condition.truthy) return isTruthyValue(dependent);
  return isTruthyValue(dependent);
}

function getChildFields(raw) {
  if (Array.isArray(raw.fields)) return raw.fields;
  if (Array.isArray(raw.children)) return raw.children;
  if (Array.isArray(raw.properties)) return raw.properties;
  return [];
}

function getArrayItemFields(raw) {
  if (Array.isArray(raw.item_fields)) return raw.item_fields;
  if (Array.isArray(raw.items)) return raw.items;
  if (isObject(raw.items) && Array.isArray(raw.items.fields)) return raw.items.fields;
  return [];
}

function normalizeScalarField(raw, index, parentPath, parentLabel) {
  const label = String(raw.label ?? raw.title ?? raw.prompt ?? raw.name ?? raw.key ?? `Field ${index + 1}`);
  const key = String(raw.key ?? raw.name ?? raw.field ?? raw.id ?? (slugify(label) || `field_${index + 1}`));
  const keyPath = getPath(parentPath, key);
  const rawType = String(raw.type ?? 'text').trim().toLowerCase();
  const isBoolean = rawType === 'boolean' || key.toLowerCase() === 'is_applicable';
  const type = isBoolean
    ? 'boolean'
    : rawType === 'select'
      ? 'dropdown'
      : SCALAR_TYPES.has(rawType)
        ? rawType
        : 'text';

  const options = Array.isArray(raw.options)
    ? raw.options.map(normalizeOption)
    : type === 'boolean' || rawType === 'radio'
      ? [
          { label: 'Yes', value: 'Yes' },
          { label: 'No', value: 'No' },
        ]
      : [];

  const groupName = String(raw.section ?? raw.group ?? raw.category ?? parentLabel ?? '').trim()
    || (parentPath ? toLabel(parentPath.split('.').slice(-1)[0]) : 'Additional Details');

  return {
    keyPath,
    label,
    type,
    required: Boolean(raw.required),
    options,
    placeholder: typeof raw.placeholder === 'string' ? raw.placeholder : '',
    conditionalOn: normalizeCondition(raw.conditional_on),
    groupName,
    isPanField: /pan/i.test(key),
  };
}

function normalizeArrayField(raw, index, parentPath, parentLabel) {
  const label = String(raw.label ?? raw.title ?? raw.prompt ?? raw.name ?? raw.key ?? `Section ${index + 1}`);
  const key = String(raw.key ?? raw.name ?? raw.field ?? raw.id ?? (slugify(label) || `section_${index + 1}`));
  const keyPath = getPath(parentPath, key);
  const rawItemFields = getArrayItemFields(raw);
  const sourceFields = rawItemFields.length > 0 ? rawItemFields : [];

  const itemFields = sourceFields.map((field, itemIndex) => {
    const normalized = normalizeScalarField(isObject(field) ? field : { key: String(field), label: String(field) }, itemIndex, '', '');
    return {
      key: normalized.keyPath,
      label: normalized.label,
      type: normalized.type,
      required: normalized.required,
      options: normalized.options,
      placeholder: normalized.placeholder,
      isPanField: normalized.isPanField,
    };
  });

  const groupName = String(raw.section ?? raw.group ?? raw.category ?? parentLabel ?? '').trim()
    || (parentPath ? toLabel(parentPath.split('.').slice(-1)[0]) : 'Additional Details');

  return {
    keyPath,
    label,
    required: Boolean(raw.required),
    conditionalOn: normalizeCondition(raw.conditional_on),
    itemFields,
    groupName,
  };
}

function collectSchema(entries, parentPath, parentLabel, output) {
  if (!Array.isArray(entries)) return;

  entries.forEach((entry, index) => {
    const raw = isObject(entry)
      ? entry
      : { key: String(entry ?? ''), label: toLabel(String(entry ?? `field_${index + 1}`)), type: 'text' };

    const rawType = String(raw.type ?? '').trim().toLowerCase();
    const childFields = getChildFields(raw);
    const isArray =
      ARRAY_TYPES.has(rawType)
      || Array.isArray(raw.item_fields)
      || Array.isArray(raw.items)
      || (isObject(raw.items) && Array.isArray(raw.items.fields));

    if (isArray) {
      const arrayField = normalizeArrayField(raw, index, parentPath, parentLabel);
      if (arrayField.itemFields.length > 0) {
        output.arrayFields.push(arrayField);
      }
      return;
    }

    if (childFields.length > 0 && !SCALAR_TYPES.has(rawType)) {
      const childKey = String(raw.key ?? raw.name ?? raw.field ?? raw.id ?? slugify(raw.label ?? `group_${index + 1}`));
      const childPath = getPath(parentPath, childKey);
      const childLabel = String(raw.label ?? raw.title ?? raw.name ?? parentLabel ?? '').trim();
      collectSchema(childFields, childPath, childLabel, output);
      return;
    }

    output.scalarFields.push(normalizeScalarField(raw, index, parentPath, parentLabel));
  });
}

function buildSchema(schemaEntries) {
  const output = { scalarFields: [], arrayFields: [] };
  collectSchema(Array.isArray(schemaEntries) ? schemaEntries : [], '', '', output);
  return output;
}

function setNestedValue(target, path, value) {
  const parts = String(path || '').split('.').map((entry) => entry.trim()).filter(Boolean);
  if (parts.length === 0) return;

  let pointer = target;
  parts.forEach((part, index) => {
    const isLast = index === parts.length - 1;
    if (isLast) {
      pointer[part] = value;
      return;
    }
    if (!isObject(pointer[part])) {
      pointer[part] = {};
    }
    pointer = pointer[part];
  });
}

function toSubmitValue(field, rawValue) {
  const value = typeof rawValue === 'string' ? rawValue.trim() : rawValue;
  if (field.type === 'number') return value === '' ? '' : Number(value);
  if (field.type === 'boolean') {
    const normalized = String(value ?? '').trim().toLowerCase();
    if (['yes', 'true', '1'].includes(normalized)) return true;
    if (['no', 'false', '0'].includes(normalized)) return false;
    return '';
  }
  return value ?? '';
}

function sanitizePan(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10);
}

function getFieldString(value) {
  if (value == null) return '';
  return String(value);
}

function singular(label) {
  const clean = String(label || '').trim();
  if (/partners?$/i.test(clean)) return 'Partner';
  if (clean.endsWith('s')) return clean.slice(0, -1);
  return clean || 'Item';
}

function isSmeAccount(accountType) {
  return /sme/i.test(String(accountType || ''));
}

function isSmeContext(accountType, lifecycleIntent, agentMessage) {
  const searchable = `${accountType || ''} ${lifecycleIntent || ''} ${agentMessage || ''}`;
  return /sme/i.test(searchable);
}

function isStakeholderBooleanField(field) {
  if (!field) return false;
  const searchable = `${field.keyPath} ${field.label}`.toLowerCase();
  const looksLikeStakeholder = /stakeholder|partner|director/.test(searchable);
  const normalizedOptions = Array.isArray(field.options) ? field.options : [];
  const hasYesOption = normalizedOptions.some((option) => {
    const value = String(option?.value ?? '').trim().toLowerCase();
    const label = String(option?.label ?? '').trim().toLowerCase();
    return ['yes', 'true', '1'].includes(value) || label === 'yes';
  });
  const hasNoOption = normalizedOptions.some((option) => {
    const value = String(option?.value ?? '').trim().toLowerCase();
    const label = String(option?.label ?? '').trim().toLowerCase();
    return ['no', 'false', '0'].includes(value) || label === 'no';
  });
  const isBooleanLike = field.type === 'boolean' || field.type === 'radio' || (hasYesOption && hasNoOption);
  return looksLikeStakeholder && isBooleanLike;
}

export function addSmeFallbackPartnerSection(schema, accountType, context = {}) {
  const lifecycleIntent =
    typeof context.lifecycleIntent === 'string' ? context.lifecycleIntent : '';
  const agentMessage =
    typeof context.agentMessage === 'string' ? context.agentMessage : '';

  if (!isSmeContext(accountType, lifecycleIntent, agentMessage)) {
    return schema.arrayFields;
  }

  const hasPartnerSection = schema.arrayFields.some((section) =>
    /partner|director|stakeholder/i.test(`${section.keyPath} ${section.label}`)
  );
  if (hasPartnerSection) {
    return schema.arrayFields;
  }

  const stakeholderField = schema.scalarFields.find(isStakeholderBooleanField);
  if (!stakeholderField) {
    return schema.arrayFields;
  }

  return [
    ...schema.arrayFields,
      {
        keyPath: 'partners',
        label: 'Additional Stakeholders (Partners / Directors)',
        required: true,
        conditionalOn: {
          field: stakeholderField.keyPath,
          truthy: true,
        },
        itemFields: DEFAULT_SME_PARTNER_FIELDS,
        groupName: 'Additional Details',
      },
  ];
}

export default function AdditionalInfoFormView({
  agentMessage,
  dataRequired,
  extractedData,
  isSubmitting,
  onSubmit,
}) {
  const formSchema = Array.isArray(extractedData?.form_schema) ? extractedData.form_schema : dataRequired;
  const accountType = typeof extractedData?.account_type === 'string' ? extractedData.account_type : '';
  const lifecycleIntent = typeof extractedData?.lifecycle_intent === 'string' ? extractedData.lifecycle_intent : '';
  const schema = useMemo(() => buildSchema(formSchema), [formSchema]);
  const scalarFields = schema.scalarFields;
  const arrayFields = useMemo(
    () => addSmeFallbackPartnerSection(schema, accountType, { lifecycleIntent, agentMessage }),
    [accountType, agentMessage, lifecycleIntent, schema]
  );

  const [values, setValues] = useState({});
  const [arrayValues, setArrayValues] = useState({});
  const [touched, setTouched] = useState({});
  const [submitError, setSubmitError] = useState('');

  useEffect(() => {
    setValues((prev) =>
      scalarFields.reduce((acc, field) => {
        acc[field.keyPath] = Object.prototype.hasOwnProperty.call(prev, field.keyPath) ? prev[field.keyPath] : '';
        return acc;
      }, {})
    );

    setArrayValues((prev) =>
      arrayFields.reduce((acc, section) => {
        const existing = Array.isArray(prev[section.keyPath]) ? prev[section.keyPath] : [];
        acc[section.keyPath] = existing.map((item) =>
          section.itemFields.reduce((itemAcc, field) => {
            itemAcc[field.key] = item[field.key] ?? '';
            return itemAcc;
          }, {})
        );
        return acc;
      }, {})
    );

    setTouched({});
    setSubmitError('');
  }, [scalarFields, arrayFields]);

  const scalarVisibility = useMemo(
    () =>
      scalarFields.reduce((acc, field) => {
        acc[field.keyPath] = evaluateCondition(field.conditionalOn, values);
        return acc;
      }, {}),
    [scalarFields, values]
  );

  const arrayVisibility = useMemo(
    () =>
      arrayFields.reduce((acc, section) => {
        acc[section.keyPath] = evaluateCondition(section.conditionalOn, values);
        return acc;
      }, {}),
    [arrayFields, values]
  );

  const validationErrors = useMemo(() => {
    const errors = {};

    scalarFields.forEach((field) => {
      if (scalarVisibility[field.keyPath] === false) return;
      const value = getFieldString(values[field.keyPath]).trim();
      if (field.required && !value) {
        errors[field.keyPath] = `${field.label} is required.`;
        return;
      }
      if (value && field.type === 'number' && Number.isNaN(Number(value))) {
        errors[field.keyPath] = `${field.label} must be a valid number.`;
        return;
      }
      if (value && field.isPanField && !PAN_PATTERN.test(value.toUpperCase())) {
        errors[field.keyPath] = `${field.label} must be a valid PAN (10 characters).`;
      }
    });

    arrayFields.forEach((section) => {
      if (arrayVisibility[section.keyPath] === false) return;

      const sectionItems = Array.isArray(arrayValues[section.keyPath]) ? arrayValues[section.keyPath] : [];
      if (section.required && sectionItems.length === 0) {
        errors[`${section.keyPath}.__section`] = `Add at least one ${section.label.toLowerCase()} entry.`;
      }

      sectionItems.forEach((item, index) => {
        section.itemFields.forEach((field) => {
          const value = getFieldString(item[field.key]).trim();
          const errorKey = `${section.keyPath}.${index}.${field.key}`;
          if (field.required && !value) {
            errors[errorKey] = `${field.label} is required.`;
            return;
          }
          if (value && field.type === 'number' && Number.isNaN(Number(value))) {
            errors[errorKey] = `${field.label} must be a valid number.`;
            return;
          }
          if (value && field.isPanField && !PAN_PATTERN.test(value.toUpperCase())) {
            errors[errorKey] = `${field.label} must be a valid PAN (10 characters).`;
          }
        });
      });
    });

    return errors;
  }, [arrayFields, arrayValues, scalarFields, scalarVisibility, values, arrayVisibility]);

  const groupedScalars = useMemo(() => {
    const groups = new Map();
    scalarFields.forEach((field) => {
      const groupName = field.groupName || 'Additional Details';
      if (!groups.has(groupName)) {
        groups.set(groupName, []);
      }
      groups.get(groupName).push(field);
    });
    return Array.from(groups.entries()).map(([name, fields]) => ({ name, fields }));
  }, [scalarFields]);

  const hasFields = scalarFields.length > 0 || arrayFields.length > 0;
  const canSubmit = hasFields && Object.keys(validationErrors).length === 0 && !isSubmitting;

  const handleScalarChange = (field, nextValue) => {
    const value = field.isPanField ? sanitizePan(nextValue) : nextValue;
    setValues((prev) => ({ ...prev, [field.keyPath]: value }));
    setTouched((prev) => ({ ...prev, [field.keyPath]: true }));
  };

  const handleAddArrayItem = (section) => {
    const emptyItem = section.itemFields.reduce((acc, field) => ({ ...acc, [field.key]: '' }), {});
    setArrayValues((prev) => ({
      ...prev,
      [section.keyPath]: [...(Array.isArray(prev[section.keyPath]) ? prev[section.keyPath] : []), emptyItem],
    }));
    setTouched((prev) => ({ ...prev, [`${section.keyPath}.__section`]: true }));
  };

  const handleRemoveArrayItem = (section, index) => {
    setArrayValues((prev) => ({
      ...prev,
      [section.keyPath]: (Array.isArray(prev[section.keyPath]) ? prev[section.keyPath] : []).filter((_, idx) => idx !== index),
    }));
  };

  const handleArrayValueChange = (section, index, field, nextValue) => {
    const value = field.isPanField ? sanitizePan(nextValue) : nextValue;
    setArrayValues((prev) => {
      const nextItems = [...(Array.isArray(prev[section.keyPath]) ? prev[section.keyPath] : [])];
      nextItems[index] = {
        ...(nextItems[index] || {}),
        [field.key]: value,
      };
      return {
        ...prev,
        [section.keyPath]: nextItems,
      };
    });
    setTouched((prev) => ({ ...prev, [`${section.keyPath}.${index}.${field.key}`]: true }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const allTouched = {};
    scalarFields.forEach((field) => {
      allTouched[field.keyPath] = true;
    });
    arrayFields.forEach((section) => {
      allTouched[`${section.keyPath}.__section`] = true;
      const sectionItems = Array.isArray(arrayValues[section.keyPath]) ? arrayValues[section.keyPath] : [];
      sectionItems.forEach((item, index) => {
        section.itemFields.forEach((field) => {
          allTouched[`${section.keyPath}.${index}.${field.key}`] = true;
        });
      });
    });
    setTouched(allTouched);

    if (typeof onSubmit !== 'function' || Object.keys(validationErrors).length > 0 || !hasFields) {
      return;
    }

    setSubmitError('');

    try {
      const finalData = {};

      scalarFields.forEach((field) => {
        if (scalarVisibility[field.keyPath] === false) return;
        setNestedValue(finalData, field.keyPath, toSubmitValue(field, values[field.keyPath]));
      });

      arrayFields.forEach((section) => {
        if (arrayVisibility[section.keyPath] === false) return;

        const rows = (Array.isArray(arrayValues[section.keyPath]) ? arrayValues[section.keyPath] : [])
          .map((row) =>
            section.itemFields.reduce((acc, field) => {
              acc[field.key] = toSubmitValue(field, row[field.key]);
              return acc;
            }, {})
          )
          .filter((row) => Object.values(row).some((value) => !(value === '' || value == null)));

        setNestedValue(finalData, section.keyPath, rows);
      });

      await onSubmit('SYSTEM: SUBMIT_ADDITIONAL_INFO', {
        source: 'submit_additional_info',
        hidden: true,
        command: 'SUBMIT_ADDITIONAL_INFO',
        finalData,
      });
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Unable to submit details right now.');
    }
  };

  return (
    <div className={styles.viewCard}>
      <h2 className={styles.viewTitle}>Additional Information</h2>
      <p className={styles.agentMessage}>
        {agentMessage || 'Please complete the requested details to continue.'}
      </p>
      {(accountType || lifecycleIntent) && (
        <p className={styles.metaText}>
          {`Context: ${[accountType, lifecycleIntent].filter(Boolean).join(' | ')}`}
        </p>
      )}

      {submitError && <p className={styles.errorText}>{submitError}</p>}

      <form className={styles.reviewForm} onSubmit={handleSubmit} noValidate>
        {!hasFields && <p className={styles.metaText}>No additional fields were returned by the backend.</p>}

        {groupedScalars.map((group) => (
          <section key={group.name} className={styles.reviewSection}>
            {(groupedScalars.length > 1 || group.name !== 'Additional Details') && (
              <h3 className={styles.reviewSectionTitle}>{group.name}</h3>
            )}

            <div className={styles.reviewGrid}>
              {group.fields.map((field) => {
                const isVisible = scalarVisibility[field.keyPath] !== false;
                const value = getFieldString(values[field.keyPath]);
                const showError = touched[field.keyPath] && validationErrors[field.keyPath];

                return (
                  <div key={field.keyPath} className={`${styles.reviewField} ${!isVisible ? styles.hiddenField : ''}`}>
                    {field.type === 'dropdown' ? (
                      <div className={`${styles.muiInputWrapper} ${styles.muiSelectWrapper} ${value ? styles.hasValue : ''}`}>
                        <select
                          id={`additional-${slugify(field.keyPath)}`}
                          className={`${styles.muiInput} ${styles.muiSelect}`}
                          value={value}
                          disabled={isSubmitting || !isVisible}
                          onChange={(event) => handleScalarChange(field, event.target.value)}
                        >
                          <option value="">Select an option</option>
                          {field.options.map((option) => (
                            <option key={`${field.keyPath}_${option.value}`} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <label className={styles.muiLabel} htmlFor={`additional-${slugify(field.keyPath)}`}>
                          {field.label}
                        </label>
                      </div>
                    ) : field.type === 'radio' || field.type === 'boolean' ? (
                      <div>
                        <label className={styles.label}>{field.label}</label>
                        <div className={styles.radioGroup}>
                          {field.options.map((option) => (
                            <label key={`${field.keyPath}_${option.value}`} className={styles.radioOption}>
                              <input
                                type="radio"
                                name={field.keyPath}
                                value={option.value}
                                checked={value === option.value}
                                disabled={isSubmitting || !isVisible}
                                onChange={(event) => handleScalarChange(field, event.target.value)}
                              />
                              <span>{option.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className={`${styles.muiInputWrapper} ${value || field.type === 'date' ? styles.hasValue : ''}`}>
                        <input
                          id={`additional-${slugify(field.keyPath)}`}
                          className={styles.muiInput}
                          type={field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text'}
                          value={value}
                          placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                          disabled={isSubmitting || !isVisible}
                          maxLength={field.isPanField ? 10 : undefined}
                          onChange={(event) => handleScalarChange(field, event.target.value)}
                        />
                        <label className={styles.muiLabel} htmlFor={`additional-${slugify(field.keyPath)}`}>
                          {field.label}
                        </label>
                      </div>
                    )}

                    {showError && <p className={styles.errorText}>{validationErrors[field.keyPath]}</p>}
                  </div>
                );
              })}
            </div>
          </section>
        ))}

        {arrayFields.map((section) => {
          const isVisible = arrayVisibility[section.keyPath] !== false;
          const sectionItems = Array.isArray(arrayValues[section.keyPath]) ? arrayValues[section.keyPath] : [];
          const sectionErrorKey = `${section.keyPath}.__section`;
          const showSectionError = touched[sectionErrorKey] && validationErrors[sectionErrorKey];
          const addLabel = /partners?/i.test(section.label) ? 'Add Partner' : `Add ${singular(section.label)}`;

          return (
            <section key={section.keyPath} className={`${styles.reviewSection} ${!isVisible ? styles.hiddenField : ''}`}>
              <div className={styles.reviewSectionHeader}>
                <h3 className={styles.reviewSectionTitle}>{section.label}</h3>
                <button
                  type="button"
                  className={`${styles.primaryBtn} ${styles.secondaryBtn}`}
                  onClick={() => handleAddArrayItem(section)}
                  disabled={isSubmitting || !isVisible}
                >
                  {addLabel}
                </button>
              </div>

              {sectionItems.length === 0 && <p className={styles.metaText}>No entries added yet.</p>}

              <div className={styles.arrayList}>
                {sectionItems.map((item, index) => (
                  <div key={`${section.keyPath}_${index}`} className={styles.arrayItemCard}>
                    <div className={styles.arrayItemHeader}>
                      <h4 className={styles.arrayItemTitle}>{`${singular(section.label)} ${index + 1}`}</h4>
                      <button
                        type="button"
                        className={styles.linkBtn}
                        onClick={() => handleRemoveArrayItem(section, index)}
                        disabled={isSubmitting}
                      >
                        Remove
                      </button>
                    </div>

                    <div className={styles.reviewGrid}>
                      {section.itemFields.map((field) => {
                        const value = getFieldString(item[field.key]);
                        const errorKey = `${section.keyPath}.${index}.${field.key}`;
                        const showError = touched[errorKey] && validationErrors[errorKey];

                        return (
                          <div key={`${section.keyPath}_${index}_${field.key}`} className={styles.reviewField}>
                            {field.type === 'dropdown' ? (
                              <div className={`${styles.muiInputWrapper} ${styles.muiSelectWrapper} ${value ? styles.hasValue : ''}`}>
                                <select
                                  id={`${section.keyPath}-${index}-${field.key}`}
                                  className={`${styles.muiInput} ${styles.muiSelect}`}
                                  value={value}
                                  disabled={isSubmitting}
                                  onChange={(event) => handleArrayValueChange(section, index, field, event.target.value)}
                                >
                                  <option value="">Select an option</option>
                                  {field.options.map((option) => (
                                    <option key={`${section.keyPath}_${index}_${field.key}_${option.value}`} value={option.value}>
                                      {option.label}
                                    </option>
                                  ))}
                                </select>
                                <label className={styles.muiLabel} htmlFor={`${section.keyPath}-${index}-${field.key}`}>
                                  {field.label}
                                </label>
                              </div>
                            ) : (
                              <div className={`${styles.muiInputWrapper} ${value || field.type === 'date' ? styles.hasValue : ''}`}>
                                <input
                                  id={`${section.keyPath}-${index}-${field.key}`}
                                  className={styles.muiInput}
                                  type={field.type === 'number' ? 'number' : 'text'}
                                  value={value}
                                  placeholder={field.placeholder || `Enter ${field.label.toLowerCase()}`}
                                  maxLength={field.isPanField ? 10 : undefined}
                                  disabled={isSubmitting}
                                  onChange={(event) => handleArrayValueChange(section, index, field, event.target.value)}
                                />
                                <label className={styles.muiLabel} htmlFor={`${section.keyPath}-${index}-${field.key}`}>
                                  {field.label}
                                </label>
                              </div>
                            )}

                            {showError && <p className={styles.errorText}>{validationErrors[errorKey]}</p>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>

              {showSectionError && <p className={styles.errorText}>{validationErrors[sectionErrorKey]}</p>}
            </section>
          );
        })}

        <button className={styles.primaryBtn} type="submit" disabled={!canSubmit}>
          {isSubmitting ? 'Submitting...' : 'Submit Details'}
        </button>
      </form>
    </div>
  );
}
