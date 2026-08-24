package com.neuronova.quizbible.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import com.neuronova.quizbible.data.local.AppThemeMode

private val PrimaryBlue = Color(0xFF1E3A8A)
private val SecondaryAmber = Color(0xFFD97706)
private val BackgroundLight = Color(0xFFF8FAFC)
private val SurfaceLight = Color(0xFFFFFFFF)
private val TextPrimaryLight = Color(0xFF0F172A)
private val TextSecondaryLight = Color(0xFF475569)

private val PrimaryBlueDark = Color(0xFF60A5FA)
private val SecondaryAmberDark = Color(0xFFFBBF24)
private val BackgroundDark = Color(0xFF0F172A)
private val SurfaceDark = Color(0xFF1E293B)
private val TextPrimaryDark = Color(0xFFF8FAFC)
private val TextSecondaryDark = Color(0xFF94A3B8)

// High Contrast Theme
private val HighContrastBackground = Color(0xFF000000)
private val HighContrastSurface = Color(0xFF121212)
private val HighContrastPrimary = Color(0xFFFFFF00)
private val HighContrastSecondary = Color(0xFF00FFFF)
private val HighContrastText = Color(0xFFFFFFFF)

// Semantic colors
val CorrectGreen = Color(0xFF16A34A)
val IncorrectRed = Color(0xFFDC2626)
val VerifiedBlue = Color(0xFF2563EB)
val CardBorderColor = Color(0xFFE2E8F0)

private val LightColorScheme = lightColorScheme(
    primary = PrimaryBlue,
    secondary = SecondaryAmber,
    background = BackgroundLight,
    surface = SurfaceLight,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onBackground = TextPrimaryLight,
    onSurface = TextPrimaryLight
)

private val DarkColorScheme = darkColorScheme(
    primary = PrimaryBlueDark,
    secondary = SecondaryAmberDark,
    background = BackgroundDark,
    surface = SurfaceDark,
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onBackground = TextPrimaryDark,
    onSurface = TextPrimaryDark
)

private val HighContrastColorScheme = darkColorScheme(
    primary = HighContrastPrimary,
    secondary = HighContrastSecondary,
    background = HighContrastBackground,
    surface = HighContrastSurface,
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onBackground = HighContrastText,
    onSurface = HighContrastText
)

@Composable
fun QuizBibleTheme(
    themeMode: AppThemeMode = AppThemeMode.LIGHT,
    content: @Composable () -> Unit
) {
    val colorScheme = when (themeMode) {
        AppThemeMode.LIGHT -> LightColorScheme
        AppThemeMode.DARK -> DarkColorScheme
        AppThemeMode.HIGH_CONTRAST -> HighContrastColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}
