{
  "project_name": "Gaian Wealth-Flow: Mission Control",
  "deployment_target": "zo.space (splashdown.zo.space/mission)",
  "app_type": "Interactive Web App + Arcade Simulation",
  "core_objective": "Transform the mission page into a playable, real-time arcade simulation with progression, retention, and optional monetization.",
  "app_structure": {
    "routes": [
      { "path": "/mission", "component": "MainGameCanvas", "description": "Primary gameplay interface" },
      { "path": "/dashboard", "component": "PlayerStats", "description": "Wallet, progress, stats" },
      { "path": "/upgrades", "component": "UpgradeShop", "description": "Spend points to enhance gameplay" }
    ]
  },
  "game_engine": {
    "rendering": "HTML5 Canvas",
    "loop": "requestAnimationFrame",
    "tick_rate": 60
  },
  "core_systems": {
    "gaian_pulse": {
      "interval_seconds": 26,
      "effects": [
        "Trigger global visual pulse",
        "Activate 2x scoring window (3 seconds)",
        "Reset partial entity positions"
      ]
    },
    "volatility_system": {
      "mode": "Simulated",
      "states": [
        { "name": "Calm", "spawn_rate": 0.5, "enemy_speed": 0.6 },
        { "name": "Active", "spawn_rate": 1.0, "enemy_speed": 1.0 },
        { "name": "Chaotic", "spawn_rate": 1.8, "enemy_speed": 1.6 }
      ],
      "cycle": "randomized every 30-90 seconds"
    }
  },
  "entities": {
    "player": {
      "movement": "WASD",
      "abilities": ["Harvest (auto)", "P = Supernova", "SPACE = Shield"]
    },
    "jade_orbs": {
      "function": "Score pickups",
      "value_range": [1, 50],
      "behavior": "Drifting motion"
    },
    "red_nian": {
      "function": "Damage entities",
      "behavior": "Erratic movement",
      "damage": "Wallet reduction"
    }
  },
  "economy": {
    "wallet": {
      "start": 10,
      "soft_cap": 1000000
    },
    "multipliers": {
      "combo": "Increase per successful pickup",
      "risk_reward": "Higher difficulty = higher payout"
    }
  },
  "progression": {
    "levels": [
      { "name": "Initiate", "unlock": 0 },
      { "name": "Operator", "unlock": 1000 },
      { "name": "Architect", "unlock": 10000 },
      { "name": "Vanguard", "unlock": 100000 }
    ],
    "upgrades": [
      "Movement speed boost",
      "Orb magnet radius",
      "Shield duration increase",
      "Pulse cooldown reduction"
    ]
  },
  "monetization": {
    "model": "Optional (non-pay-to-win)",
    "methods": [
      { "type": "Cosmetics", "examples": ["Ship skins", "Orb styles", "UI themes"] },
      { "type": "Supporter Pack", "price": "$3-10", "reward": "Visual upgrades + minor QoL (no advantage)" }
    ]
  },
  "retention_features": {
    "daily_challenges": [
      "Collect 500 orbs",
      "Survive 5 minutes in chaotic mode"
    ],
    "leaderboard": "High score tracking",
    "session_tracking": true
  },
  "ui_design": {
    "theme": "Cyber-noir HUD",
    "elements": [
      "Wallet counter",
      "Pulse countdown",
      "Volatility meter",
      "Combo tracker"
    ]
  },
  "technical_requirements": {
    "responsive": true,
    "mobile_support": true,
    "save_system": "LocalStorage (initial), upgrade to cloud later"
  },
  "success_metrics": {
    "engagement": "Average session > 3 minutes",
    "retention": "Return users within 24h",
    "conversion": "Optional supporter purchases"
  }
}
