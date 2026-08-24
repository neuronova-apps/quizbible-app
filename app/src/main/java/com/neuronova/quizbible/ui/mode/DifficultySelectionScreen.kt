package com.neuronova.quizbible.ui.mode

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neuronova.quizbible.data.model.DifficultyFilter
import com.neuronova.quizbible.data.model.GameMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DifficultySelectionScreen(
    mode: GameMode,
    onDifficultySelected: (DifficultyFilter) -> Unit,
    onBackClick: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(mode.title, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Atrás")
                    }
                }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text(
                    text = "Selecciona el nivel de dificultad para la partida (10 preguntas):",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
                    modifier = Modifier.padding(vertical = 8.dp)
                )
            }

            items(DifficultyFilter.values()) { diff ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onDifficultySelected(diff) },
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = diff.displayName,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = when (diff) {
                                    DifficultyFilter.ALL -> "Preguntas de todos los niveles combinadas al azar"
                                    DifficultyFilter.BASIC -> "Conceptos bíblicos fundamentales y hechos conocidos"
                                    DifficultyFilter.INTERMEDIATE -> "Conocimiento bíblico general estructurado"
                                    DifficultyFilter.ADVANCED -> "Detalles de relatos, genealogías y profecías"
                                    DifficultyFilter.EXPERT -> "Detalles textuales minuciosos y contextos profundos"
                                },
                                fontSize = 13.sp,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                            )
                        }
                        Icon(
                            Icons.Default.ChevronRight,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.6f)
                        )
                    }
                }
            }
        }
    }
}
