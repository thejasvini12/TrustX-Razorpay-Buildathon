import {
  SimulatorScenarioDefinition,
  SimulatorScenarioId,
} from '../types/simulator';
import { PRESET_SCENARIOS } from '../components/account-risk/ScenarioPresets';
import { FRAUD_PRESETS } from '../components/fraud-spike/FraudScenarioPresets';
import { RING_PRESETS } from '../components/abuse-ring/AbuseRingScenarioPresets';

// Helper lookups reusing existing benchmark payloads
const getAccountPreset = (id: string) => PRESET_SCENARIOS.find((p) => p.id === id)?.data;
const getFraudPreset = (id: string) => FRAUD_PRESETS.find((p) => p.id === id)?.data;
const getRingPreset = (id: string) => RING_PRESETS.find((p) => p.id === id)?.data;

/**
 * Registry of 7 strongly typed attack and benchmark scenarios for the Unified Simulator.
 * All payloads reuse the verified, existing benchmark templates.
 */
export const SIMULATOR_SCENARIOS: SimulatorScenarioDefinition[] = [
  // 1. Legitimate Buyer
  {
    id: 'legitimate_buyer',
    name: 'Legitimate Customer & Clean Traffic',
    shortDescription: 'Established consumer placing normal orders with standard device and payment history.',
    attackCategory: 'BENIGN_TRAFFIC',
    severity: 'LOW',
    involvedEngines: ['ACCOUNT_RISK', 'FRAUD_SPIKE', 'ABUSE_RING'],
    stages: [
      {
        stageNumber: 1,
        engine: 'ACCOUNT_RISK',
        title: 'Account & Return Risk Evaluation',
        description: 'Verify baseline account trustworthiness, standard shopping volume, and low return rates.',
      },
      {
        stageNumber: 2,
        engine: 'FRAUD_SPIKE',
        title: 'Merchant Cluster Traffic Audit',
        description: 'Ensure merchant-level velocity and dispute rate remain within standard 1% baseline.',
      },
      {
        stageNumber: 3,
        engine: 'ABUSE_RING',
        title: 'Entity Disconnection Audit',
        description: 'Confirm zero cross-account collusion across hardware, IP, or payment tokens.',
      },
    ],
    accountRiskPayload: getAccountPreset('legitimate_buyer'),
    fraudSpikePayload: getFraudPreset('normal_merchant'),
    abuseRingPayload: getRingPreset('clean_independent'),
    demoObjective: 'Demonstrate frictionless processing and zero false positives across all 3 engines for standard retail customers.',
    operationalStory: 'Healthy customer tenure (340 days), single device, and standard payment card produce consistent ALLOW actions across all defense layers.',
    keyDifferentiatorNote: 'Frictionless baseline alignment across account, return, cluster, and graph engines.',
    referenceOutput: {
      expectedAccountAction: 'ALLOW',
      expectedReturnAction: 'ALLOW_STANDARD_RETURNS',
      expectedSpikeAction: 'ALLOW_STANDARD_OPERATIONS',
      expectedRingAction: 'NO_ACTION',
      referenceInsight: 'All 3 defense engines agree on customer legitimacy. No operational friction required.',
    },
  },

  // 2. Serial Wardrober
  {
    id: 'serial_wardrober',
    name: 'Serial Wardrobing & Return Abuse',
    shortDescription: 'Frequent high-value apparel returns with short retention cycle and shared return drop address.',
    attackCategory: 'RETURN_ABUSE',
    severity: 'MEDIUM',
    involvedEngines: ['ACCOUNT_RISK', 'ABUSE_RING'],
    stages: [
      {
        stageNumber: 1,
        engine: 'ACCOUNT_RISK',
        title: 'Specialized Wardrobing Assessment',
        description: 'Evaluate post-purchase return frequency (77.8% return rate) against account-level checkout privileges.',
      },
      {
        stageNumber: 2,
        engine: 'ABUSE_RING',
        title: 'Shared Drop Destination Audit',
        description: 'Detect coordinated multi-account apparel return cluster sharing residential apartment drop address.',
      },
    ],
    accountRiskPayload: getAccountPreset('serial_wardrober'),
    abuseRingPayload: getRingPreset('wardrober_cluster'),
    demoObjective: 'Showcase domain orthogonal separation: account-level checkout remains reviewable while post-purchase return privileges are restricted.',
    operationalStory: 'Buyer purchases expensive merchandise ($161 AOV) but returns 14 of 18 orders. Return Risk triggers FLAG_FOR_RETURN_DESK_AUDIT while Abuse Ring flags the shared return drop.',
    keyDifferentiatorNote: 'Post-purchase loss prevention operates independently without shutting down buying privileges prematurely.',
    referenceOutput: {
      expectedAccountAction: 'MANUAL_REVIEW',
      expectedReturnAction: 'FLAG_FOR_RETURN_DESK_AUDIT',
      expectedRingAction: 'REVIEW_CLUSTER',
      referenceInsight: 'Domain separation in action: checkout is not hard-blocked, but physical return inspection is mandated.',
    },
  },

  // 3. Promo Exploitation Farm
  {
    id: 'promo_farm',
    name: 'Promo Voucher Exploitation Syndicate',
    shortDescription: 'Sybil multi-accounting farm creating dormant accounts to drain new-user registration credits.',
    attackCategory: 'PROMO_ABUSE',
    severity: 'CRITICAL',
    involvedEngines: ['ACCOUNT_RISK', 'ABUSE_RING'],
    stages: [
      {
        stageNumber: 1,
        engine: 'ACCOUNT_RISK',
        title: 'Single-Account Feature Scoring',
        description: 'Evaluate individual bot account with minimal spend ($42 across 3 orders) in isolation.',
      },
      {
        stageNumber: 2,
        engine: 'ABUSE_RING',
        title: 'Bipartite Token Collusion Sentinel',
        description: 'Analyze graph topology linking 4 accounts to a single cloned mobile IMEI and locker address.',
      },
    ],
    accountRiskPayload: getAccountPreset('promo_bot'),
    abuseRingPayload: getRingPreset('promo_farm'),
    demoObjective: 'Demonstrate the platform key differentiator: single-row ML scores early bot as LOW (Score 17), but graph topology catches the syndicate as CRITICAL (0.8240).',
    operationalStory: 'In isolation, account ACC_SYNTH_PROMO_BOT_9104 has no bad history and low spend ($42). However, Abuse Ring Sentinel uncovers a 4-account clique sharing DEV_FARM_CLONED_IMEI and enforces BLOCK_ENTIRE_RING.',
    keyDifferentiatorNote: 'Single-row ML models have a blind spot on low-history sybils; Bipartite Graph Sentinel closes this gap completely.',
    referenceOutput: {
      expectedAccountAction: 'ALLOW',
      expectedReturnAction: 'ALLOW_STANDARD_RETURNS',
      expectedRingAction: 'BLOCK_ENTIRE_RING',
      referenceInsight: 'Single-row ML blind spot resolved by Graph Syndicate Sentinel. Device hardware token blacklisted.',
    },
  },

  // 4. Card Testing Syndicate
  {
    id: 'card_testing',
    name: 'Automated Card Testing Velocity Surge',
    shortDescription: 'High-velocity emulator bot rapidly cycling stolen card tokens from a Tor exit node.',
    attackCategory: 'CARD_TESTING',
    severity: 'HIGH',
    involvedEngines: ['FRAUD_SPIKE', 'ABUSE_RING', 'ACCOUNT_RISK'],
    stages: [
      {
        stageNumber: 1,
        engine: 'FRAUD_SPIKE',
        title: 'P5 5-Minute Micro-Burst Radar',
        description: 'Detect 7x transaction velocity surge and 35% fraud spike in latest 5-minute sub-window.',
      },
      {
        stageNumber: 2,
        engine: 'ABUSE_RING',
        title: 'Proxy & Card Churn Sentinel',
        description: 'Identify 3 scripter accounts rapidly cycling credit cards through DEV_SCRIPTER_BOX_01 and IP_TOR_EXIT_NODE_44.',
      },
      {
        stageNumber: 3,
        engine: 'ACCOUNT_RISK',
        title: 'Account Step-Up Enforcement',
        description: 'Enforce cryptographic proof-of-work and step-up challenges on high-anomaly emulator bots.',
      },
    ],
    accountRiskPayload: getAccountPreset('syndicate_mule'),
    fraudSpikePayload: getFraudPreset('five_min_burst'),
    abuseRingPayload: getRingPreset('card_testing'),
    demoObjective: 'Show multi-layered temporal and graph coordination during an active automated card-testing run.',
    operationalStory: 'Hourly volume looks borderline, but P5 5-minute telemetry detects rapid card testing velocity (+35% fraud rate), while Abuse Ring isolates the Tor proxy cluster.',
    keyDifferentiatorNote: 'Sub-window telemetry catches micro-bursts before 1-hour rollups trigger.',
    referenceOutput: {
      expectedSpikeAction: 'FLAG_FOR_VELOCITY_AUDIT_AND_MONITOR',
      expectedRingAction: 'REVIEW_CLUSTER',
      expectedAccountAction: 'CHALLENGE_OR_BLOCK',
      referenceInsight: 'Multi-layer defense: 5-minute radar detects surge, graph identifies proxy network, account engine challenges bot.',
    },
  },

  // 5. Persistent Fraud Incident
  {
    id: 'persistent_incident',
    name: 'Persistent Multi-Window Merchant Attack',
    shortDescription: 'Repeated velocity surges across consecutive evaluation windows triggering P3 stateful escalation.',
    attackCategory: 'PERSISTENT_ATTACK',
    severity: 'HIGH',
    involvedEngines: ['FRAUD_SPIKE'],
    stages: [
      {
        stageNumber: 1,
        engine: 'FRAUD_SPIKE',
        title: 'Evaluation Window 1: Initial Anomaly',
        description: 'First anomalous window observed (Score: 45 MEDIUM, Counter: 1 of 3). Action: FLAG_FOR_VELOCITY.',
        isSequential: true,
      },
      {
        stageNumber: 2,
        engine: 'FRAUD_SPIKE',
        title: 'Evaluation Window 2: Sustained Pressure',
        description: 'Second anomalous window observed (Score: 45 MEDIUM, Counter: 2 of 3). Action: FLAG_FOR_VELOCITY.',
        isSequential: true,
      },
      {
        stageNumber: 3,
        engine: 'FRAUD_SPIKE',
        title: 'Evaluation Window 3: Automatic P3 Escalation',
        description: 'Third consecutive anomalous window triggers stateful policy escalation to HIGH (Score: 75, Action: ENABLE_STRICT_RATE_LIMITS_AND_2FA).',
        isSequential: true,
        iterationCount: 3,
      },
    ],
    fraudSpikePayload: getFraudPreset('persistent_incident'),
    demoObjective: 'Demonstrate P3 rolling merchant incident tracking and automatic escalation from passive monitoring to strict rate limiting.',
    operationalStory: 'A merchant under repeated attack triggers MEDIUM risk across 3 sequential evaluation windows. The stateful tracker increments consecutive windows and automatically escalates the final policy recommendation to HIGH.',
    keyDifferentiatorNote: 'Stateful rolling persistence prevents continuous low-grade attacks from slipping under the radar.',
    referenceOutput: {
      expectedSpikeAction: 'ENABLE_STRICT_RATE_LIMITS_AND_2FA',
      referenceInsight: 'P3 Persistence Escalation: 3 consecutive anomalous windows triggered automated tier escalation to strict enforcement.',
    },
  },

  // 6. High-Risk Syndicate Mule
  {
    id: 'syndicate_mule',
    name: 'High-Density Identity Mule Syndicate',
    shortDescription: 'Coordinated syndicate utilizing emulator farms, VPNs, stolen card BINs, and drop address suites.',
    attackCategory: 'COORDINATED_SYNDICATE',
    severity: 'CRITICAL',
    involvedEngines: ['ACCOUNT_RISK', 'ABUSE_RING'],
    stages: [
      {
        stageNumber: 1,
        engine: 'ACCOUNT_RISK',
        title: 'Account Anomaly & Instrument Scoring',
        description: 'Score lead mule account exhibiting 6 devices, 7 IPs, crypto cards, and 0.96 suspicious score.',
      },
      {
        stageNumber: 2,
        engine: 'ABUSE_RING',
        title: 'Bipartite Clique & 4-Gate Enforcement',
        description: 'Verify 4/4 safety gates (critical confidence, 0 bystanders, multi-modal tokens) to execute BLOCK_ENTIRE_RING.',
      },
    ],
    accountRiskPayload: getAccountPreset('syndicate_mule'),
    abuseRingPayload: getRingPreset('identity_ring'),
    demoObjective: 'Demonstrate high-confidence full-syndicate shutdown when all 4 enforcement gates pass with zero bystanders.',
    operationalStory: 'A 4-account synthetic identity ring operates across shared emulator boxes and stolen card BINs. The account engine assigns Score 100 HIGH, while Abuse Ring confirms 0 bystanders and executes BLOCK_ENTIRE_RING.',
    keyDifferentiatorNote: 'Gated 4-way check ensures full syndicate blocks only execute with 100% confidence and 0 bystanders.',
    referenceOutput: {
      expectedAccountAction: 'CHALLENGE_OR_BLOCK',
      expectedRingAction: 'BLOCK_ENTIRE_RING',
      referenceInsight: 'All 4 enforcement gates satisfied (High Confidence, 0 Bystanders, Multi-Modal). Full ring block enforced.',
    },
  },

  // 7. Shared-IP Family / Bystander Protection
  {
    id: 'shared_family_bystander',
    name: 'Shared Infrastructure & Bystander Protection',
    shortDescription: 'Legitimate family / campus roommates sharing WiFi router and physical address with diverse cards.',
    attackCategory: 'BYSTANDER_PROTECTION',
    severity: 'LOW',
    involvedEngines: ['ACCOUNT_RISK', 'ABUSE_RING'],
    stages: [
      {
        stageNumber: 1,
        engine: 'ACCOUNT_RISK',
        title: 'Household Member Scoring',
        description: 'Verify individual account health, clean transaction history, and normal retail spending.',
      },
      {
        stageNumber: 2,
        engine: 'ABUSE_RING',
        title: 'Bystander Isolation & Safe Attribution',
        description: 'Ensure shared common-carrier network (residential WiFi router) isolates members as protected INCIDENTAL_BYSTANDER.',
      },
    ],
    accountRiskPayload: getAccountPreset('legitimate_buyer'),
    abuseRingPayload: getRingPreset('shared_family_bystander'),
    demoObjective: 'Prove that shared common-carrier infrastructure (IP/Address) does NOT cause false-positive syndicate blocks.',
    operationalStory: 'Parent, student, and sibling share IP_HOME_WIFI_ROUTER_12 and ADDR_HOME_OAK_ST_104. The Abuse Ring Sentinel recognizes benign infrastructure, applies -0.05 mitigation delta, and classifies all 3 members as INCIDENTAL_BYSTANDER.',
    keyDifferentiatorNote: 'Deterministic bystander isolation prevents innocent co-located roommates and family members from being blocked.',
    referenceOutput: {
      expectedAccountAction: 'ALLOW',
      expectedRingAction: 'NO_ACTION',
      referenceInsight: 'Bystander protection active: all accounts designated INCIDENTAL_BYSTANDER. Zero false-positive enforcement.',
    },
  },
];

/**
 * Lookup helper to retrieve scenario definition by ID.
 */
export function getSimulatorScenario(id: SimulatorScenarioId): SimulatorScenarioDefinition | undefined {
  return SIMULATOR_SCENARIOS.find((s) => s.id === id);
}
