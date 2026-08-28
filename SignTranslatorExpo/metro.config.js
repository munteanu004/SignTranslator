const path = require('path');
const { getDefaultConfig } = require('expo/metro-config');

const projectRoot = __dirname;
const mobileAppRoot = path.resolve(projectRoot, '..', 'mobile_app');

const config = getDefaultConfig(projectRoot);

config.watchFolders = [mobileAppRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, 'node_modules'),
  path.resolve(mobileAppRoot, 'node_modules'),
];

module.exports = config;
