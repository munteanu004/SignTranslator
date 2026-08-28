import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  StatusBar,
  ScrollView,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

const AccountScreen = () => {
  return (
    <ScrollView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor="#FFFFFF" />

      {/* Profile Header */}
      <View style={styles.header}>
        <View style={styles.profileImageContainer}>
          <View style={styles.profileImage}>
            <Icon name="account" size={60} color="#45C8C2" />
          </View>
          <View style={styles.editBadge}>
            <Icon name="pencil" size={16} color="#FFFFFF" />
          </View>
        </View>
        <Text style={styles.profileName}>Emma Bernard</Text>
      </View>

      {/* Settings List */}
      <View style={styles.settingsList}>
        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Text style={styles.settingLabel}>Profile name</Text>
            <Text style={styles.settingValue}>Emma Bernard</Text>
          </View>
          <Icon name="chevron-right" size={24} color="#999999" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Text style={styles.settingLabel}>App language</Text>
            <Text style={styles.settingValue}>English</Text>
          </View>
          <Icon name="chevron-right" size={24} color="#999999" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Text style={styles.settingLabel}>Sign language</Text>
            <Text style={styles.settingValue}>ASL</Text>
          </View>
          <Icon name="chevron-right" size={24} color="#999999" />
        </TouchableOpacity>

        <TouchableOpacity style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Text style={styles.settingLabel}>Are you hearing</Text>
            <Text style={styles.settingValue}>Yes</Text>
          </View>
          <Icon name="chevron-right" size={24} color="#999999" />
        </TouchableOpacity>

        <View style={styles.divider} />

        <TouchableOpacity style={styles.logoutButton}>
          <Text style={styles.logoutLabel}>Logout</Text>
          <Text style={styles.logoutSubtext}>Logout of your account</Text>
          <Icon
            name="logout"
            size={24}
            color="#666666"
            style={styles.logoutIcon}
          />
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
  },
  header: {
    alignItems: 'center',
    paddingTop: 60,
    paddingBottom: 30,
  },
  profileImageContainer: {
    position: 'relative',
    marginBottom: 16,
  },
  profileImage: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  editBadge: {
    position: 'absolute',
    bottom: 0,
    right: 0,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#45C8C2',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: '#FFFFFF',
  },
  profileName: {
    fontSize: 24,
    fontWeight: '600',
    color: '#111111',
  },
  settingsList: {
    paddingHorizontal: 20,
    paddingTop: 20,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F0F0',
  },
  settingLeft: {
    flex: 1,
  },
  settingLabel: {
    fontSize: 16,
    color: '#111111',
    fontWeight: '500',
    marginBottom: 4,
  },
  settingValue: {
    fontSize: 14,
    color: '#666666',
  },
  divider: {
    height: 20,
  },
  logoutButton: {
    position: 'relative',
    paddingVertical: 16,
  },
  logoutLabel: {
    fontSize: 16,
    color: '#111111',
    fontWeight: '500',
    marginBottom: 4,
  },
  logoutSubtext: {
    fontSize: 14,
    color: '#666666',
  },
  logoutIcon: {
    position: 'absolute',
    right: 0,
    top: 20,
  },
});

export default AccountScreen;
