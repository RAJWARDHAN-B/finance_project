import { describe, it, expect, vi } from 'vitest'
import { manageComponent } from './index.js'
import { QUICK_SUGGESTION_ACTIONS } from '../../../../../../../../utils/constants/quickSuggestionAction.js'
import { COMPONENT_REGISTRY_TYPES } from '../../../../../../../../utils/constants/componentRegistry.js'
import { ROLE } from '../../../../../../../../utils/constants/roles.js'

describe('manageComponent', () => {
  it('adds all tyre follow-up messages when their config is present', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [
          { sku: 'sku-1' },
          { sku: 'sku-2' },
          { sku: 'sku-3' },
          { sku: 'sku-4' },
        ],
        vehicles: [{ label: 'e-208' }],
        links: [{ title: 'TRP', type: 'Link', url: 'https://example.com' }],
      },
    }
    const config = {
      tyre_RecommendationMessage_by_vehicle_plural:
        '{{brand}} tyres for {{label}}',
      tyre_AvailabilityMessage_by_vehicle_plural: '{{totalTyres}} available',
      message_suggestion_feedback: 'Give us your feedback',
    }

    manageComponent(messageState, message, config)

    // Verify updateLastBotMessage called with recommendation message
    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
        componentProps: expect.objectContaining({
          content: expect.any(String),
          metadata: message.metadata,
          id: undefined,
        }),
      })
    )

    // Verify addBotMessage called 3 times: tyres, availability, suggestions
    expect(messageState.addBotMessage).toHaveBeenCalledTimes(3)

    // First call: tyres component
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          isStreaming: false,
          tyres: message.metadata.tyres.slice(0, 3),
        }),
      })
    )

    // Second call: availability message
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
        componentProps: expect.objectContaining({
          id: 'msg-1',
          isStreaming: false,
          content: expect.any(String),
        }),
      })
    )

    // Third call: suggestions with feedback CTA
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      3,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          isStreaming: false,
          metadata: message.metadata,
          suggestions: [
            expect.objectContaining({
              label: 'Give us your feedback',
              action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
            }),
          ],
        }),
      })
    )
  })

  it('uses generic config keys when no vehicles in metadata', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        suggestions: ['Option A'],
      },
    }
    const config = {
      tyre_RecommendationMessage_generic_singular: 'Generic recommendation',
      tyre_AvailabilityMessage_generic_singular: 'Generic availability',
      message_suggestion_feedback: 'Give us your feedback',
    }

    manageComponent(messageState, message, config)

    // Intro message is updated on the last bot message when generic config exists
    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
      })
    )

    // Tyres + availability + suggestions are sent as follow-up bot messages
    expect(messageState.addBotMessage).toHaveBeenCalledTimes(3)
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('adds tyres component with at most 3 tyres (recommendedTyres)', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const allTyres = [
      { sku: 'sku-1' },
      { sku: 'sku-2' },
      { sku: 'sku-3' },
      { sku: 'sku-4' },
      { sku: 'sku-5' },
    ]
    const message = {
      id: 'msg-1',
      metadata: { tyres: allTyres },
    }

    manageComponent(messageState, message, {})

    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: allTyres.slice(0, 3),
        }),
      })
    )
  })

  it('does not add suggestions message when no suggestionItems and no metadata suggestions', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
      },
    }

    manageComponent(messageState, message, {})

    // Product-card-only updates the latest bot message with TYRES
    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('adds feedback CTA when tyres exist and includeFeedbackSuggestion is true', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
      },
    }
    const config = {
      message_suggestion_feedback: 'Give us your feedback',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [
            expect.objectContaining({
              label: 'Give us your feedback',
              action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
            }),
          ],
        }),
      })
    )
  })

  it('adds metadata suggestions and feedback CTA in one message when both exist', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        suggestions: ['Option A', 'Option B'],
      },
    }
    const config = {
      message_suggestion_feedback: 'Give us your feedback',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [
            { label: 'Option A', promptText: 'Option A' },
            { label: 'Option B', promptText: 'Option B' },
            expect.objectContaining({
              label: 'Give us your feedback',
              action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
            }),
          ],
        }),
      })
    )
  })

  it('does not suppress intro/availability templates when only suggestions_full exists', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        vehicles: [],
        suggestions_full: [
          { label: 'Premium Sedan', value: 'premium-sedan' },
        ],
      },
    }
    const config = {
      tyre_RecommendationMessage_generic_singular: 'Generic recommendation',
      tyre_AvailabilityMessage_generic_singular: 'Generic availability',
    }

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
      })
    )

    expect(messageState.addBotMessage).toHaveBeenCalledTimes(3)
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
      })
    )
    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      3,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
      })
    )
  })

  it('handles suggestions without tyres (isSuggestions && !isTyres)', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions: ['Option A', 'Option B'],
      },
    }

    manageComponent(messageState, message, {})

    expect(messageState.addBotMessage).toHaveBeenCalledTimes(1)
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          isStreaming: false,
          metadata: message.metadata,
          suggestions: [
            { label: 'Option A', promptText: 'Option A' },
            { label: 'Option B', promptText: 'Option B' },
          ],
        }),
      })
    )
  })

  it('handles suggestions_full without tyres when legacy suggestions is missing', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [
          { label: 'Premium Sedan', value: 'premium-sedan' },
          { label: 'Premium Plus Sedan', value: 'premium-plus-sedan' },
        ],
      },
    }

    manageComponent(messageState, message, {})

    expect(messageState.addBotMessage).toHaveBeenCalledTimes(1)
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          isStreaming: false,
          metadata: message.metadata,
          suggestions: [
            { label: 'Premium Sedan', promptText: 'premium-sedan' },
            {
              label: 'Premium Plus Sedan',
              promptText: 'premium-plus-sedan',
            },
          ],
        }),
      })
    )
  })

  it('does not add feedback CTA for metadata suggestions without tyres', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions: ['Option A'],
      },
    }
    const config = {
      message_suggestion_feedback: 'Give us your feedback',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [{ label: 'Option A', promptText: 'Option A' }],
        }),
      })
    )
  })

  it('prefers suggestions_full labels and uses values as prompt text', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions: ['premium-sedan', 'premium-plus-sedan'],
        suggestions_full: [
          { label: 'Premium Sedan', value: 'premium-sedan' },
          { label: 'Premium Plus Sedan', value: 'premium-plus-sedan' },
        ],
      },
    }

    manageComponent(messageState, message, {})

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [
            { label: 'Premium Sedan', promptText: 'premium-sedan' },
            {
              label: 'Premium Plus Sedan',
              promptText: 'premium-plus-sedan',
            },
          ],
        }),
      })
    )
  })

  it('keeps old suggestions format unchanged when suggestions_full is missing', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions: ['7sp-auto-1.4l-4cyl-t-slash-petrol'],
      },
    }

    manageComponent(messageState, message, {})

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [
            {
              label: '7sp-auto-1.4l-4cyl-t-slash-petrol',
              promptText: '7sp-auto-1.4l-4cyl-t-slash-petrol',
            },
          ],
        }),
      })
    )
  })

  it('does not throw when tyres or suggestions arrays are missing', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {},
    }

    expect(() => manageComponent(messageState, message, {})).not.toThrow()
    expect(messageState.addBotMessage).not.toHaveBeenCalled()
    expect(messageState.updateLastBotMessage).not.toHaveBeenCalled()
  })

  it('skips updateLastBotMessage when tyre_RecommendationMessage is not configured', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        suggestions: ['Option A'],
      },
    }

    manageComponent(messageState, message, {})

    expect(messageState.updateLastBotMessage).not.toHaveBeenCalled()

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('skips availability message when tyre_AvailabilityMessage is not configured', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ brand: 'michelin', sku: 'sku-1' }],
        vehicles: [{ label: 'e-208' }],
      },
    }
    const config = {
      tyre_RecommendationMessage_by_vehicle_singular:
        '{{brand}} tyres for {{label}}',
    }

    manageComponent(messageState, message, config)

    // Should add tyres component message, but not availability or suggestions
    expect(messageState.addBotMessage).toHaveBeenCalledTimes(1)
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('product-card-only: updates last bot message with TYRE and hides intro/availability', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        vehicles: [],
        suggestions: [],
      },
    }
    // No intro or availability messages configured
    const config = {}

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [{ sku: 'sku-1' }],
        }),
      })
    )

    expect(messageState.addBotMessage).toHaveBeenCalledTimes(0)
  })

  it('product-card-only: keeps only give feedback suggestion when configured', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        vehicles: [],
        suggestions: [],
      },
    }
    const config = {
      message_suggestion_feedback: 'Give us your feedback',
    }

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
    expect(messageState.addBotMessage).toHaveBeenCalledTimes(1)
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [
            expect.objectContaining({
              label: 'Give us your feedback',
              action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
            }),
          ],
        }),
      })
    )

    const suggestionPayload = messageState.addBotMessage.mock.calls[0][0]
    expect(suggestionPayload.componentProps.suggestions).toHaveLength(1)
    expect(suggestionPayload.componentProps.suggestions[0]).toEqual({
      label: 'Give us your feedback',
      action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
    })
  })

  it('preserves the textual answer when metadata requests it', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        show_textual_answer: true,
      },
    }
    const config = {
      tyre_RecommendationMessage_generic_singular: 'Recommended tyre',
      tyre_AvailabilityMessage_generic_singular: 'One tyre available',
    }

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).not.toHaveBeenCalled()
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [{ sku: 'sku-1' }],
        }),
      })
    )
  })

  it('adds product info message before tyres when metadata contains reifen links', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        vehicles: [{ label: 'e-208' }],
        reifen: {
          serviceInformation: 'http://example.com/service-information.pdf',
          previousTyreApprovals: 'http://example.com/previous-approvals.pdf',
        },
      },
    }
    const config = {
      tyre_RecommendationMessage_by_vehicle_singular:
        '{{brand}} tyres for {{label}}',
      reifenfreigabe_show_reifen_info: true,
      reifenfreigabe_info:
        'Discover documents relative to tire release. {{see_documents}}',
      reifenfreigabe_drawer_heading: 'Information on tire approval',
      reifenfreigabe_see_documents: 'See documents',
      reifenfreigabe_doc_serviceinfo: 'Service Information',
      reifenfreigabe_doc_previous_tyre_info: 'Previous Tyre Approvals',
    }

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
      })
    )

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.REIFENFREIGABE_INFO,
        componentProps: expect.objectContaining({
          reifenfreigabeInfo: config.reifenfreigabe_info,
          drawerHeading: config.reifenfreigabe_drawer_heading,
          seeDocumentsButtonLabel: config.reifenfreigabe_see_documents,
          reifenfreigabeDocumentsData: {
            documents: [
              {
                heading: 'Service Information',
                attachment: {
                  src: 'http://example.com/service-information.pdf',
                },
              },
              {
                heading: 'Previous Tyre Approvals',
                attachment: {
                  src: 'http://example.com/previous-approvals.pdf',
                },
              },
            ],
          },
        }),
      })
    )

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('does not replace last message with tyres when reifen info message is present', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        reifen: {
          serviceInformation: 'http://example.com/service-information.pdf',
        },
      },
    }
    const config = {
      reifenfreigabe_show_reifen_info: true,
      reifenfreigabe_info: 'See documents {{see_documents}}',
    }

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).not.toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.REIFENFREIGABE_INFO,
      })
    )
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('does not add reifen info when payload has no mapped documents', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        reifen: {
          unknownKey: 'http://example.com/unknown.pdf',
        },
      },
    }
    const config = {
      reifenfreigabe_show_reifen_info: true,
      reifenfreigabe_info: 'See documents {{see_documents}}',
      reifenfreigabe_doc_serviceinfo: 'Service Information',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).not.toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.REIFENFREIGABE_INFO,
      })
    )
    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('maps reifen document headings from flat config keys', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1' }],
        reifen: {
          serviceInformation: 'http://example.com/service-information.pdf',
          manufacturerCertificate: 'http://example.com/manufacturer.pdf',
        },
      },
    }
    const config = {
      reifenfreigabe_show_reifen_info: true,
      reifenfreigabe_info: 'See documents {{see_documents}}',
      reifenfreigabe_doc_serviceinfo: 'Service Information Label',
      reifenfreigabe_doc_manufacturer_certificate:
        'Manufacturer Certificate Label',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.REIFENFREIGABE_INFO,
        componentProps: expect.objectContaining({
          reifenfreigabeDocumentsData: {
            documents: [
              {
                heading: 'Service Information Label',
                attachment: {
                  src: 'http://example.com/service-information.pdf',
                },
              },
              {
                heading: 'Manufacturer Certificate Label',
                attachment: {
                  src: 'http://example.com/manufacturer.pdf',
                },
              },
            ],
          },
        }),
      })
    )
  })

  it('builds suggestion prompts from suggestions_full values', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [
          { label: 'Year 2020', value: '2020' },
          { label: 'Year 2021', value: '2021' },
        ],
      },
    }

    manageComponent(messageState, message, {})

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: expect.objectContaining({
          suggestions: [
            { label: 'Year 2020', promptText: '2020' },
            { label: 'Year 2021', promptText: '2021' },
          ],
        }),
      })
    )
  })

  it('auto-selects a single matching suggestions_full option from last user prompt', () => {
    const messageState = {
      messages: [
        {
          componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
          componentProps: {
            role: ROLE.USER,
            content: 'BMW 1 Series (F20/F21) Saloon 2019',
          },
        },
      ],
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const conversationState = {
      messageToSend: null,
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [{ label: '(F20/F21) Saloon', value: '(F20/F21) Saloon' }],
      },
    }

    manageComponent(messageState, message, {}, conversationState)

    expect(conversationState.messageToSend).toEqual({
      promptText: '(F20/F21) Saloon',
      silentUserMessage: true,
    })
    expect(messageState.addBotMessage).not.toHaveBeenCalled()
  })

  it('does not auto-select when multiple suggestions_full options match prompt', () => {
    const messageState = {
      messages: [
        {
          componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
          componentProps: {
            role: ROLE.USER,
            content: 'BMW (F20/F21) Saloon Touring',
          },
        },
      ],
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const conversationState = {
      messageToSend: null,
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [
          { label: '(F20/F21) Saloon', value: '(F20/F21) Saloon' },
          { label: 'Saloon Touring', value: 'Saloon Touring' },
        ],
      },
    }

    manageComponent(messageState, message, {}, conversationState)

    expect(conversationState.messageToSend).toBeNull()
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
      })
    )
  })

  it('does not auto-select when prompt is only a partial subset of a suggestion', () => {
    const messageState = {
      messages: [
        {
          componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
          componentProps: {
            role: ROLE.USER,
            content: 'a3',
          },
        },
      ],
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const conversationState = {
      messageToSend: null,
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [{ label: 'A3 Saloon', value: 'A3 Saloon' }],
      },
    }

    manageComponent(messageState, message, {}, conversationState)

    expect(conversationState.messageToSend).toBeNull()
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
      })
    )
  })

  it('does not auto-select one-token suggestions already present in full prompt', () => {
    const messageState = {
      messages: [
        {
          componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
          componentProps: {
            role: ROLE.USER,
            content: 'tyre reco for audi a3 2020',
          },
        },
      ],
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const conversationState = {
      messageToSend: null,
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [{ label: 'A3', value: 'A3' }],
      },
    }

    manageComponent(messageState, message, {}, conversationState)

    expect(conversationState.messageToSend).toBeNull()
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
      })
    )
  })

  it('does not re-queue auto-selection when last user prompt already equals selected suggestion', () => {
    const messageState = {
      messages: [
        {
          componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
          componentProps: {
            role: ROLE.USER,
            content: '(F20/F21) Saloon',
          },
        },
      ],
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const conversationState = {
      messageToSend: null,
    }
    const message = {
      id: 'msg-1',
      metadata: {
        suggestions_full: [{ label: '(F20/F21) Saloon', value: '(F20/F21) Saloon' }],
      },
    }

    manageComponent(messageState, message, {}, conversationState)

    expect(conversationState.messageToSend).toBeNull()
    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
      })
    )
  })

  it('adds buyNowUrl on tyre cards when article cai and tyre_product_url are available', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1', articles: [{ cai: '740443' }] }],
        vehicles: [
          {
            maker: 'Audi',
            family: 'A3',
            variant: 'A3',
            year: 2020,
            engine: '1.0 TFSI 115',
          },
        ],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?fitment=205---55-R-16-91W',
          },
        ],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            {
              sku: 'sku-1',
              articles: [{ cai: '740443' }],
              buyNowUrl:
                'https://www.michelin.com.au/auto/dealer-locator?cai=740443',
            },
          ],
        }),
      })
    )
  })

  it('adds buyNowUrl for complete-search payload with required metadata fields', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [
          {
            sku: 'sku-1',
            articles: [{ cai: '939615' }],
          },
        ],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?maker=audi&model=a3&fitment=205---55-R-16-91W',
          },
        ],
        suggestions: [],
        suggestions_full: [],
        vehicles: [
          {
            maker: 'Audi',
            family: 'A3',
            variant: 'A3',
            year: 2020,
            engine: '1.0 TFSI 115',
            label: 'Audi A3 2020',
          },
        ],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            expect.objectContaining({
              sku: 'sku-1',
              articles: [{ cai: '939615' }],
              buyNowUrl:
                'https://www.michelin.com.au/auto/dealer-locator?cai=939615',
            }),
          ],
        }),
      })
    )
  })

  it('adds buyNowUrl when fitment link and CAI exist with empty suggestions', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [
          {
            sku: 'sku-1',
            articles: [{ cai: '939615' }],
          },
        ],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?fitment=205---55-R-16-91W',
          },
        ],
        suggestions: [],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.updateLastBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            expect.objectContaining({
              sku: 'sku-1',
              articles: [{ cai: '939615' }],
              buyNowUrl:
                'https://www.michelin.com.au/auto/dealer-locator?cai=939615',
            }),
          ],
        }),
      })
    )
  })

  it('adds buyNowUrl even when vehicle details are incomplete if fitment and CAI are present', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1', articles: [{ cai: '740443' }] }],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?fitment=205---55-R-16-91W',
          },
        ],
        suggestions: [],
        vehicles: [{ maker: 'Audi', family: 'A3', variant: 'A3', year: 2020 }],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            {
              sku: 'sku-1',
              articles: [{ cai: '740443' }],
              buyNowUrl:
                'https://www.michelin.com.au/auto/dealer-locator?cai=740443',
            },
          ],
        }),
      })
    )
  })

  it('adds buyNowUrl for completed payload without engine and variant fields', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1', articles: [{ cai: '740443' }] }],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?fitment=205---55-R-16-91W',
          },
        ],
        suggestions: [],
        vehicles: [{ maker: 'Audi', family: 'A3', year: 2020 }],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.co.uk/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            {
              sku: 'sku-1',
              articles: [{ cai: '740443' }],
              buyNowUrl:
                'https://www.michelin.co.uk/auto/dealer-locator?cai=740443',
            },
          ],
        }),
      })
    )
  })

  it('does not add buyNowUrl when fitment is partial and not fully specified', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1', articles: [{ cai: '740443' }] }],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?fitment=205---55-R-16',
          },
        ],
        suggestions: [],
        suggestions_full: [],
        vehicles: [
          {
            maker: 'Audi',
            family: 'A3',
            variant: 'A3',
            year: 2020,
            engine: '1.0 TFSI 115',
          },
        ],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            expect.objectContaining({
              sku: 'sku-1',
              articles: [{ cai: '740443' }],
            }),
          ],
        }),
      })
    )
    expect(messageState.addBotMessage.mock.calls[0][0].componentProps.tyres[0].buyNowUrl).toBeUndefined()
    expect(messageState.updateLastBotMessage).not.toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      })
    )
  })

  it('does not add buyNowUrl when fitment is missing from TRP link', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [{ sku: 'sku-1', articles: [{ cai: '740443' }] }],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-search?maker=audi&model=a3',
          },
        ],
        suggestions: [],
        suggestions_full: [],
        vehicles: [
          {
            maker: 'Audi',
            family: 'A3',
            variant: 'A3',
            year: 2020,
            engine: '1.0 TFSI 115',
          },
        ],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [{ sku: 'sku-1', articles: [{ cai: '740443' }] }],
        }),
      })
    )
  })

  it('adds buyNowUrl when fitment and cai exist even if suggestions_full is present', () => {
    const messageState = {
      addBotMessage: vi.fn(),
      updateLastBotMessage: vi.fn(),
    }
    const message = {
      id: 'msg-1',
      metadata: {
        tyres: [
          {
            sku: 'sku-1',
            articles: [{ cai: '939615' }],
          },
        ],
        links: [
          {
            title: 'TRP',
            type: 'Link',
            url: 'https://example.com/tyre-selector?fitment=bmw-f20-f21',
          },
        ],
        suggestions_full: [{ label: '(F20/F21) Saloon', value: 'saloon' }],
      },
    }
    const config = {
      tyre_product_url: 'https://www.michelin.com.au/auto/dealer-locator',
    }

    manageComponent(messageState, message, config)

    expect(messageState.addBotMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        componentType: COMPONENT_REGISTRY_TYPES.TYRES,
        componentProps: expect.objectContaining({
          tyres: [
            expect.objectContaining({
              buyNowUrl:
                'https://www.michelin.com.au/auto/dealer-locator?cai=939615',
            }),
          ],
        }),
      })
    )
  })
})


// ADDED THIS


//   it('preserves the textual answer when metadata requests it', () => {
//     const messageState = {
//       addBotMessage: vi.fn(),
//       updateLastBotMessage: vi.fn(),
//     }
//     const message = {
//       id: 'msg-1',
//       metadata: {
//         tyres: [{ sku: 'sku-1' }],
//         show_textual_answer: true,
//       },
//     }
//     const config = {
//       tyre_RecommendationMessage_generic_singular: 'Recommended tyre',
//       tyre_AvailabilityMessage_generic_singular: 'One tyre available',
//     }

//     manageComponent(messageState, message, config)

//     expect(messageState.updateLastBotMessage).not.toHaveBeenCalled()
//     expect(messageState.addBotMessage).toHaveBeenCalledWith(
//       expect.objectContaining({
//         componentType: COMPONENT_REGISTRY_TYPES.TYRES,
//         componentProps: expect.objectContaining({
//           tyres: [{ sku: 'sku-1' }],
//         }),
//       })
//     )
//   })