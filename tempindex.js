import { getTyreMessages } from './lib/getTyreData.js'
import { getReifenfreigabeData } from './lib/getReifenfreigabeData.js'
import { getTrpFitment, isCompleteFitment } from './lib/fitment.js'
import { COMPONENT_REGISTRY_TYPES } from '../../../../../../../../utils/constants/componentRegistry.js'
import { QUICK_SUGGESTION_ACTIONS } from '../../../../../../../../utils/constants/quickSuggestionAction.js'
import { ROLE } from '../../../../../../../../utils/constants/roles.js'

const buildSuggestionItem = (suggestion) =>
  typeof suggestion === 'string'
    ? { label: suggestion, promptText: suggestion }
    : {
      label: suggestion?.label ?? suggestion?.value ?? '',
      promptText: suggestion?.value ?? suggestion?.label ?? '',
    }

const hasAnyCai = (tyres = []) =>
  tyres.some(
    (tyre = {}) =>
      Array.isArray(tyre?.articles) &&
      tyre.articles.some((article = {}) => Boolean(article?.cai))
  )

const isFitmentExplicitlyComplete = (metadata = {}) => {
  const hasTyres = (metadata?.tyres?.length ?? 0) > 0
  const hasNoPendingSuggestions = (metadata?.suggestions?.length ?? 0) === 0
  const hasCai = hasAnyCai(metadata?.tyres)

  return (
    hasTyres &&
    hasNoPendingSuggestions &&
    hasCai &&
    isCompleteFitment(getTrpFitment(metadata?.links))
  )
}

const normalizeText = (value = '') =>
  String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()

const isAutoSelectableCandidate = (candidateText = '') => {
  const normalizedCandidate = normalizeText(candidateText)
  if (!normalizedCandidate) return false

  const tokens = normalizedCandidate.split(' ').filter(Boolean)

  // Avoid auto-selecting generic one-token options (for example: "A3").
  // This keeps clarification suggestions visible instead of re-sending a
  // value that may already be present in the user query.
  return tokens.length >= 2
}

const getLastUserPrompt = (messages = []) => {
  const lastUserMessage = [...messages]
    .reverse()
    .find((entry = {}) => entry?.componentProps?.role === ROLE.USER)

  return lastUserMessage?.componentProps?.content || ''
}

const getAutoSelectedSuggestion = ({
  suggestions = [],
  lastUserPrompt = '',
} = {}) => {
  const normalizedPrompt = normalizeText(lastUserPrompt)
  if (!normalizedPrompt) return null

  const candidates = suggestions.filter((suggestion = {}) => {
    const candidateText = suggestion?.label || suggestion?.promptText || ''
    const normalizedCandidate = normalizeText(candidateText)
    if (!normalizedCandidate || !isAutoSelectableCandidate(candidateText)) {
      return false
    }

    return normalizedPrompt.includes(normalizedCandidate)
  })

  return candidates.length === 1 ? candidates[0] : null
}

export const manageComponent = (
  messageState,
  message,
  config,
  conversationState = {}
) => {
  const { id, metadata = {} } = message
  const {
    tyres = [],
    vehicles = [],
    links = [],
    suggestions = [],
    suggestions_full: suggestionsFull = [],
    reifen = null,
    show_textual_answer: showTextualAnswer = false,
  } = metadata

  const normalizedSuggestions = suggestions
    .map(buildSuggestionItem)
    .filter((suggestion) => suggestion.label)
  const normalizedSuggestionsFull = suggestionsFull
    .map(buildSuggestionItem)
    .filter((suggestion) => suggestion.label)

  const shouldEnableBuyNow = isFitmentExplicitlyComplete(metadata)

  const isSuggestions = normalizedSuggestions.length > 0
  const hasFullSuggestions = normalizedSuggestionsFull.length > 0
  const isTyres = tyres.length > 0
  // Flag to determine whether to show templated messages.
  const showProductTemplatedMessages =
    isTyres &&
    !showTextualAnswer &&
    !vehicles.length &&
    !isSuggestions &&
    !hasFullSuggestions

  const buildSuggestionItems = ({ includeFeedbackSuggestion = false } = {}) => {
    const sourceSuggestions = hasFullSuggestions
      ? normalizedSuggestionsFull
      : normalizedSuggestions
    const items = [...sourceSuggestions]

    if (includeFeedbackSuggestion && config.message_suggestion_feedback) {
      items.push({
        label: config.message_suggestion_feedback,
        action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
      })
    }

    return items
  }

  const vehicleKey = vehicles.length > 0 ? 'by_vehicle' : 'generic'
  const countKey = tyres.length === 1 ? 'singular' : 'plural'
  const introMessageTemplate = showTextualAnswer || showProductTemplatedMessages
    ? ''
    : config[`tyre_RecommendationMessage_${vehicleKey}_${countKey}`]
  const availabilityMessageTemplate = showTextualAnswer || showProductTemplatedMessages
    ? ''
    : config[`tyre_AvailabilityMessage_${vehicleKey}_${countKey}`]

  if (isTyres) {
    const tyreMessages = getTyreMessages({
      vehicles,
      links,
      tyres,
      introMessageTemplate,
      availabilityMessageTemplate,
      buyNowBaseUrl: shouldEnableBuyNow ? config.tyre_product_url : '',
    })

    const { recommendedTyres, introMessage, availabilityMessage } =
      tyreMessages ?? {}

    if (introMessage) {
      messageState.updateLastBotMessage({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
        componentProps: {
          content: introMessage,
          metadata,
          id: undefined,
        },
      })
    }

    const reifenfreigabeData = config.reifenfreigabe_show_reifen_info
      ? getReifenfreigabeData(reifen, config)
      : null
    const showReifenfreigabeData = Boolean(reifenfreigabeData)

    if (showReifenfreigabeData) {
      messageState.addBotMessage({
        componentType: COMPONENT_REGISTRY_TYPES.REIFENFREIGABE_INFO,
        componentProps: {
          isStreaming: false,
          updateScroll: false,
          reifenfreigabeInfo: config.reifenfreigabe_info,
          drawerHeading: config.reifenfreigabe_drawer_heading,
          seeDocumentsButtonLabel: config.reifenfreigabe_see_documents,
          reifenfreigabeDocumentsData: reifenfreigabeData,
        },
      })
    }

    const tyreMessagePayload = {
      componentType: COMPONENT_REGISTRY_TYPES.TYRES,
      componentProps: {
        content: '',
        isStreaming: false,
        tyres: recommendedTyres,
        updateScroll: false,
      },
    }

    if (
      showProductTemplatedMessages &&
      !availabilityMessage &&
      !showReifenfreigabeData
    ) {
      messageState.updateLastBotMessage(tyreMessagePayload)
    } else {
      messageState.addBotMessage(tyreMessagePayload)
    }

    if (availabilityMessage) {
      messageState.addBotMessage({
        componentType: COMPONENT_REGISTRY_TYPES.MESSAGE,
        componentProps: {
          id,
          content: availabilityMessage,
          isStreaming: false,
          updateScroll: false,
        },
      })
    }

    const suggestionItems = buildSuggestionItems({
      includeFeedbackSuggestion: true,
    })

    if (suggestionItems.length > 0) {
      messageState.addBotMessage({
        componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
        componentProps: {
          isStreaming: false,
          metadata,
          suggestions: suggestionItems,
          updateScroll: false,
        },
      })
    }
  }

  if ((isSuggestions || hasFullSuggestions) && !isTyres) {
    if (hasFullSuggestions) {
      const lastUserPrompt = getLastUserPrompt(messageState?.messages)
      const autoSelectedSuggestion = getAutoSelectedSuggestion({
        suggestions: normalizedSuggestionsFull,
        lastUserPrompt,
      })

      if (autoSelectedSuggestion) {
        const autoSelectedPrompt =
          autoSelectedSuggestion.promptText || autoSelectedSuggestion.label
        const shouldQueueAutoSelection =
          normalizeText(lastUserPrompt) !== normalizeText(autoSelectedPrompt)

        if (shouldQueueAutoSelection) {
          conversationState.messageToSend = {
            promptText: autoSelectedPrompt,
            silentUserMessage: true,
          }
          return
        }
      }
    }

    messageState.addBotMessage({
      componentType: COMPONENT_REGISTRY_TYPES.SUGGESTIONS,
      componentProps: {
        isStreaming: false,
        metadata,
        suggestions: buildSuggestionItems(),
        updateScroll: false,
      },
    })
  }
}




// ADDED THIS

// export const manageComponent = (
//   messageState,
//   message,
//   config,
//   conversationState = {}
// ) => {
//   const { id, metadata = {} } = message
//   const {
//     tyres = [],
//     vehicles = [],
//     links = [],
//     suggestions = [],
//     suggestions_full: suggestionsFull = [],
//     reifen = null,
//     show_textual_answer: showTextualAnswer = false,
//   } = metadata

//   const normalizedSuggestions = suggestions
//     .map(buildSuggestionItem)
//     .filter((suggestion) => suggestion.label)
//   const normalizedSuggestionsFull = suggestionsFull
//     .map(buildSuggestionItem)
//     .filter((suggestion) => suggestion.label)

//   const shouldEnableBuyNow = isFitmentExplicitlyComplete(metadata)

//   const isSuggestions = normalizedSuggestions.length > 0
//   const hasFullSuggestions = normalizedSuggestionsFull.length > 0
//   const isTyres = tyres.length > 0
//   // Flag to determine whether to show templated messages.
//   const showProductTemplatedMessages =
//     isTyres &&
//     !showTextualAnswer &&
//     !vehicles.length &&
//     !isSuggestions &&
//     !hasFullSuggestions

//   const buildSuggestionItems = ({ includeFeedbackSuggestion = false } = {}) => {
//     const sourceSuggestions = hasFullSuggestions
//       ? normalizedSuggestionsFull
//       : normalizedSuggestions
//     const items = [...sourceSuggestions]

//     if (includeFeedbackSuggestion && config.message_suggestion_feedback) {
//       items.push({
//         label: config.message_suggestion_feedback,
//         action: QUICK_SUGGESTION_ACTIONS.goToFeedbackScreen,
//       })
//     }

//     return items
//   }

//   const vehicleKey = vehicles.length > 0 ? 'by_vehicle' : 'generic'
//   const countKey = tyres.length === 1 ? 'singular' : 'plural'
//   const introMessageTemplate = showTextualAnswer || showProductTemplatedMessages
//     ? ''
//     : config[`tyre_RecommendationMessage_${vehicleKey}_${countKey}`]
//   const availabilityMessageTemplate = showTextualAnswer || showProductTemplatedMessages
//     ? ''
//     : config[`tyre_AvailabilityMessage_${vehicleKey}_${countKey}`]

//   if (isTyres) {
//     const tyreMessages = getTyreMessages({
//       vehicles,
//       links,
//       tyres,
//       introMessageTemplate,
//       availabilityMessageTemplate,
//       buyNowBaseUrl: shouldEnableBuyNow ? config.tyre_product_url : '',
//     })