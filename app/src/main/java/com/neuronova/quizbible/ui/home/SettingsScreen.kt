package com.neuronova.quizbible.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neuronova.quizbible.data.local.AppSettings
import com.neuronova.quizbible.data.local.AppThemeMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    settings: AppSettings,
    onThemeChanged: (AppThemeMode) -> Unit,
    onTextScaleChanged: (Float) -> Unit,
    onBackClick: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Configuración", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Atrás")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Theme Setting
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(text = "Tema Visual", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = settings.themeMode == AppThemeMode.LIGHT,
                            onClick = { onThemeChanged(AppThemeMode.LIGHT) },
                            label = { Text("Día") }
                        )
                        FilterChip(
                            selected = settings.themeMode == AppThemeMode.DARK,
                            onClick = { onThemeChanged(AppThemeMode.DARK) },
                            label = { Text("Noche") }
                        )
                        FilterChip(
                            selected = settings.themeMode == AppThemeMode.HIGH_CONTRAST,
                            onClick = { onThemeChanged(AppThemeMode.HIGH_CONTRAST) },
                            label = { Text("Alto Contraste") }
                        )
                    }
                }
            }

            // Text Size Setting
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(text = "Tamaño de Texto", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        FilterChip(
                            selected = settings.textScale == 1.0f,
                            onClick = { onTextScaleChanged(1.0f) },
                            label = { Text("Normal (100%)") }
                        )
                        FilterChip(
                            selected = settings.textScale == 1.15f,
                            onClick = { onTextScaleChanged(1.15f) },
                            label = { Text("Grande (115%)") }
                        )
                        FilterChip(
                            selected = settings.textScale == 1.30f,
                            onClick = { onTextScaleChanged(1.30f) },
                            label = { Text("Muy Grande (130%)") }
                        )
                    }
                }
            }

            // Version Information
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(20.dp)) {
                    Text(text = "Información del Banco Bíblico", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = "Traducción: Reina-Valera 1960 (RVR1960)", fontSize = 14.sp)
                    Text(text = "Canon: Protestante (66 Libros, 1189 Capítulos)", fontSize = 14.sp)
                    Text(text = "Preguntas Totales: 3847 preguntas", fontSize = 14.sp)
                    Text(text = "Versión del Banco: QUIZ_BIBLE_PROTESTANT_RVR1960_V1", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f))
                }
            }
        }
    }
}
