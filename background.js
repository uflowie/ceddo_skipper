chrome.runtime.onInstalled.addListener(() => {
  const RULE = {
    id: 1,
    condition: {
      initiatorDomains: ['youtube.com'],
      requestDomains: ['youtube.com', 'youtube-nocookie.com'],
      resourceTypes: ['sub_frame'],
    },
    action: {
      type: 'modifyHeaders',
      requestHeaders: [
        { header: 'Referer', value: 'asdasd', operation: 'set' }, // referer is required, player fails with error 153 otherwise; actual value does not matter
      ],
    },
  };
  chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: [RULE.id],
    addRules: [RULE],
  });
});
