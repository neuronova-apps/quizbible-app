# Proguard rules for Quiz Bible
-keepattributes *Annotation*
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
