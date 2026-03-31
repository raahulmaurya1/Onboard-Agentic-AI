import { addSmeFallbackPartnerSection } from './AdditionalInfoFormView';

describe('addSmeFallbackPartnerSection', () => {
  const stakeholderSchema = {
    scalarFields: [
      {
        keyPath: 'business.has_additional_stakeholders',
        label: 'Any additional stakeholders?',
        type: 'radio',
        options: [
          { label: 'Yes', value: 'Yes' },
          { label: 'No', value: 'No' },
        ],
      },
    ],
    arrayFields: [],
  };

  test('adds fallback partners section for SME when stakeholder field exists', () => {
    const result = addSmeFallbackPartnerSection(stakeholderSchema, 'SME');
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      keyPath: 'partners',
      label: 'Additional Stakeholders (Partners / Directors)',
      required: true,
      conditionalOn: {
        field: 'business.has_additional_stakeholders',
        truthy: true,
      },
    });
    expect(result[0].itemFields.map((field) => field.key)).toEqual(['name', 'pan', 'role']);
  });

  test('does not add fallback section for non-SME account type', () => {
    const result = addSmeFallbackPartnerSection(stakeholderSchema, 'INDIVIDUAL');
    expect(result).toEqual([]);
  });

  test('adds fallback section when SME is inferred from agent message', () => {
    const result = addSmeFallbackPartnerSection(stakeholderSchema, '', {
      agentMessage: 'To complete your SME account, provide your business details below.',
    });
    expect(result).toHaveLength(1);
    expect(result[0].keyPath).toBe('partners');
  });

  test('does not add duplicate partner section when backend already provides one', () => {
    const schemaWithPartnerSection = {
      ...stakeholderSchema,
      arrayFields: [
        {
          keyPath: 'business.partners',
          label: 'Partners',
          itemFields: [],
        },
      ],
    };
    const result = addSmeFallbackPartnerSection(schemaWithPartnerSection, 'SME');
    expect(result).toHaveLength(1);
    expect(result[0].keyPath).toBe('business.partners');
  });
});
