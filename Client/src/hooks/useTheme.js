/**
 * Theme Hook for Global Color Management
 * 
 * Provides centralized theme management with consistent colors across all components.
 */

import { useMemo } from 'react';
import { getThemeColors, getThemeCSSProperties } from '../theme/colors';

export const useTheme = (isDarkMode) => {
  const colors = useMemo(() => getThemeColors(isDarkMode), [isDarkMode]);
  const cssProperties = useMemo(() => getThemeCSSProperties(isDarkMode), [isDarkMode]);
  
  return {
    colors,
    cssProperties,
    isDarkMode
  };
};

export default useTheme;
