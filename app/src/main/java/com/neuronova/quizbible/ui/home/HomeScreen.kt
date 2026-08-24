package com.neuronova.quizbible.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun HomeScreen(
    onPlayClick: () -> Unit,
    onProgressClick: () -> Unit,
    onSettingsClick: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Header
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(top = 40.dp)
            ) {
                Text(
                    text = "QUIZ BIBLE",
                    fontSize = 36.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary,
                    letterSpacing = 2.sp
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Aprende y pon a prueba tu conocimiento bíblico",
                    fontSize = 15.sp,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f)
                )
                Spacer(modifier = Modifier.height(16.dp))
                Badge(
                    containerColor = MaterialTheme.colorScheme.secondary.copy(alpha = 0.15f),
                    contentColor = MaterialTheme.colorScheme.secondary
                ) {
                    Text(
                        text = "Reina-Valera 1960 • 66 Libros • 3847 Preguntas",
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 12.sp
                    )
                }
            }

            // Main Actions
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Button(
                    onClick = onPlayClick,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(64.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Icon(Icons.Default.PlayArrow, contentDescription = null, modifier = Modifier.size(28.dp))
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(text = "JUGAR", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                }

                OutlinedButton(
                    onClick = onProgressClick,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Icon(Icons.Default.BarChart, contentDescription = null, modifier = Modifier.size(22.dp))
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(text = "PROGRESO Y ESTADÍSTICAS", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }

                OutlinedButton(
                    onClick = onSettingsClick,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    shape = RoundedCornerShape(16.dp)
                ) {
                    Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(22.dp))
                    Spacer(modifier = Modifier.width(10.dp))
                    Text(text = "CONFIGURACIÓN", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            // Footer
            Text(
                text = "Banco Oficial RVR1960 V1 • 100% Offline",
                fontSize = 12.sp,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.5f),
                modifier = Modifier.padding(bottom = 16.dp)
            )
        }
    }
}
